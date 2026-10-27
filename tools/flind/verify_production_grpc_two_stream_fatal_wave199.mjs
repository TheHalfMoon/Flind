// Wave199: actual first-party WorkerIngestServer, GrpcStreamIngestDriver
// and PromiseScheduler over two concurrent real HTTP/2 streams. Synthetic
// source events/pipeline only; no production Kafka/ClickHouse claim.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { Code, createClient } from '@connectrpc/connect'
import { createGrpcTransport } from '@connectrpc/connect-node'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import {
  WorkerIngest, IngestStreamRequestSchema, StreamHelloSchema, SubBatchSchema,
  KafkaMessageSchema,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const scheduler=new PromiseScheduler()
const pending=[], completed=[], feeds=[]
let fastFailureLostFromPending=false
let originalFatal=null
let syntheticCallbackError=null
function emit(item){
  if(pending.length)pending.shift()(item)
  else completed.push(item)
}
async function fireSyntheticFailure(){
  try{
    // Give both real gRPC readers time to register their batch as accepted.
    const rejected=Promise.reject(new Error('wave199 synthetic global disk failure'))
    scheduler.schedule(rejected)
    await rejected.catch(()=>{})
    await Promise.resolve()
    fastFailureLostFromPending=scheduler.promises.size===0
    assert.ok(fastFailureLostFromPending)
    const first=feeds[0]
    emit({
      elements:first.batch.map(entry=>({context:entry.context,result:entry.result})),
      batchContext:first.batchContext,sideEffects:[],
    })
  }catch(error){syntheticCallbackError=error}
}
const pipeline={
  async feed(batch,batchContext,budget){
    assert.equal(batch.length,1)
    assert.equal(batch[0].context.message.topic,'flind_wave199_synthetic')
    assert.ok([199,200].includes(batch[0].context.message.offset))
    assert.equal(batch[0].context.message.value.toString(),'{"event":"$pageview"}')
    assert.equal(budget.softAt,Infinity)
    feeds.push({batch,batchContext})
    if(feeds.length===2){
      assert.notEqual(feeds[0].batchContext.grpcStreamId,feeds[1].batchContext.grpcStreamId)
      setTimeout(()=>void fireSyntheticFailure(),35)
    }
    return {ok:true}
  },
  next(){
    if(completed.length)return Promise.resolve(completed.shift())
    return new Promise(resolve=>pending.push(resolve))
  },
}
const driver=new GrpcStreamIngestDriver(pipeline,scheduler)
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,drainTimeoutMs:350,pumpIdleMs:1},
  {driver,onFatal:error=>{originalFatal=error}},
)
function hello(clientIndex){
  return create(IngestStreamRequestSchema,{
    msg:{case:'hello',value:create(StreamHelloSchema,{
      consumerId:'flind-wave199-consumer-'+clientIndex,streamEpoch:1n,
    })},
  })
}
function batch(clientIndex){
  return create(IngestStreamRequestSchema,{
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:1n,batchId:'flind-wave199-batch-'+clientIndex,
      messages:[create(KafkaMessageSchema,{
        topic:'flind_wave199_synthetic',partition:0,
        offset:BigInt(199+clientIndex),timestamp:1761500000000n,
        key:'flind:synthetic',value:'{"event":"$pageview"}',headers:{},
      })],
      assignmentEpoch:1n,replay:false,softBudgetMs:0n,
    })},
  })
}
async function* frames(i){yield hello(i);yield batch(i)}
try{
  await server.start()
  const port=server.server.address().port
  assert.ok(port>0)
  const client=createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+port,httpVersion:'2',
  }))
  async function run(i){
    const responseTypes=[]
    let thrown=null
    try{
      for await(const reply of client.ingestStream(frames(i))){
        responseTypes.push(reply.msg.case)
      }
    }catch(error){thrown=error}
    return {responseTypes,thrown}
  }
  const firstAndSecond=await Promise.all([run(0),run(1)])
  assert.equal(syntheticCallbackError,null)
  assert.equal(feeds.length,2,'must admit two independent real gRPC batches')
  assert.ok(fastFailureLostFromPending,'must reproduce early settled failure')
  for(const stream of firstAndSecond){
    assert.equal(stream.responseTypes[0],'ready','real stream must become ready')
    assert.equal(stream.responseTypes.includes('ack'),false,
      'poisoned production pipeline must not ACK either in-flight stream')
    assert.ok(stream.thrown,'both original gRPC streams must fail')
    assert.equal(stream.thrown.code,Code.Internal)
  }
  assert.ok(originalFatal instanceof Error)
  assert.match(originalFatal.message,/wave199 synthetic global disk failure/)
  const later=await run(2)
  assert.equal(later.responseTypes.includes('ack'),false)
  assert.equal(later.thrown?.code,Code.Unavailable)
  process.stdout.write(JSON.stringify({
    phase:'wave199_original_two_grpc_streams_fail_together',
    original_product_server_used:true,
    original_product_driver_used:true,
    original_product_scheduler_used:true,
    concurrent_real_http2_streams:2,
    both_batches_fed_before_fatal:true,
    synthetic_failure_cleared_before_ack_barrier:true,
    no_ack_to_either_stream:true,
    both_real_streams_fail_internal:true,
    post_fatal_new_stream_unavailable:true,
    production_joined_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    durable_clickhouse_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{await server.stop()}
