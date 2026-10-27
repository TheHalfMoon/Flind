// Wave198: original Flind gRPC server + original production driver + original
// PromiseScheduler over real HTTP/2, but synthetic pipeline and event only.
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

const scheduler = new PromiseScheduler()
const waiters=[], completed=[]
let feeds=0
let vanishedBeforeNext=false
let fatal=null
const pipeline={
  async feed(batch,batchContext,budget){
    assert.equal(batch.length,1)
    assert.equal(batch[0].context.message.topic,'flind_wave198_synthetic')
    assert.equal(batch[0].context.message.offset,198)
    assert.equal(batch[0].context.message.value.toString(), '{"event":"$pageview"}')
    assert.equal(batchContext.grpcSeq,1)
    assert.equal(budget.softAt,Infinity)
    feeds++
    // Real first-party scheduler, but synthetic already-failed side effect.
    // The rejection cleanup occurs BEFORE the real production driver calls
    // waitForAll(). Old scheduler accidentally ACKed this exact case.
    const reject=Promise.reject(new Error('wave198 synthetic disk write failed'))
    scheduler.schedule(reject)
    await reject.catch(()=>{})
    await Promise.resolve()
    vanishedBeforeNext=scheduler.promises.size===0
    assert.ok(vanishedBeforeNext,'must prove the rejected promise left the pending set')
    const item={
      elements:batch.map(entry=>({context:entry.context,result:entry.result})),
      batchContext,
      sideEffects:[],
    }
    if(waiters.length)waiters.shift()(item)
    else completed.push(item)
    return {ok:true}
  },
  next(){
    if(completed.length) return Promise.resolve(completed.shift())
    return new Promise(resolve=>waiters.push(resolve))
  },
}
const driver=new GrpcStreamIngestDriver(pipeline,scheduler)
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,drainTimeoutMs:300,pumpIdleMs:1},
  {driver,onFatal:error=>{fatal=error}},
)
function hello(){
  return create(IngestStreamRequestSchema,{
    msg:{case:'hello',value:create(StreamHelloSchema,{
      consumerId:'flind-wave198-original-grpc',streamEpoch:1n,
    })},
  })
}
function batch(){
  return create(IngestStreamRequestSchema,{
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:1n,batchId:'flind-wave198-fast-reject',
      messages:[create(KafkaMessageSchema,{
        topic:'flind_wave198_synthetic',partition:0,offset:198n,
        timestamp:1761500000000n,key:'flind:synthetic',
        value:'{"event":"$pageview"}',headers:{},
      })],
      assignmentEpoch:1n,replay:false,softBudgetMs:0n,
    })},
  })
}
async function* frames(){yield hello();yield batch()}
try{
  await server.start()
  const port=server.server.address().port
  assert.ok(port>0)
  const client=createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+port,httpVersion:'2',
  }))
  const responseTypes=[]
  let rejected=null
  try{
    for await(const reply of client.ingestStream(frames())){
      responseTypes.push(reply.msg.case)
    }
  }catch(error){rejected=error}
  assert.equal(feeds,1,'must feed the real production gRPC driver exactly once')
  assert.ok(vanishedBeforeNext,'must reproduce the fast failed side-effect window')
  assert.equal(responseTypes[0],'ready')
  assert.equal(responseTypes.includes('ack'),false,'failed durable side effect must NEVER be acked')
  assert.ok(rejected,'client must see the fatal gRPC stream outcome')
  assert.equal(rejected.code,Code.Internal)
  assert.ok(fatal instanceof Error,'server fatal callback must be reached')
  assert.match(fatal.message,/wave198 synthetic disk write failed/)
  // After the original server was poisoned, a new connection cannot hide
  // the earlier durable failure and manufacture an ACK.
  let subsequent=null
  try{
    for await(const reply of client.ingestStream(frames())) {
      if(reply.msg.case==='ack')throw Error('post-fatal ACK leaked')
    }
  }catch(error){subsequent=error}
  assert.ok(subsequent,'post-fatal streams must fail')
  assert.equal(subsequent.code,Code.Unavailable)
  process.stdout.write(JSON.stringify({
    phase:'wave198_original_grpc_fast_rejected_side_effect',
    original_product_server_used:true,
    original_product_driver_used:true,
    original_product_scheduler_used:true,
    real_http2_proto_stream_used:true,
    rejection_cleaned_before_wait:true,
    no_ack_after_early_rejected_side_effect:true,
    original_server_fatal_callback:true,
    post_fatal_new_stream_refused:true,
    production_joined_pipeline_qualified:false,
    durable_clickhouse_qualified:false,
    production_rust_consumer_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{await server.stop()}
