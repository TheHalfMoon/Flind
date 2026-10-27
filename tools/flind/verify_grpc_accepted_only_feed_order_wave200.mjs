// Wave200: actual first-party gRPC server, production driver and
// FeedOrderSentinel over real HTTP/2. Synthetic in-memory pipeline only.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { createClient } from '@connectrpc/connect'
import { createGrpcTransport } from '@connectrpc/connect-node'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import { FeedOrderSentinel } from './firstparty/nodejs/src/ingestion/api/feed-order-sentinel.ts'
import {
  WorkerIngest, IngestStreamRequestSchema, StreamHelloSchema,
  SubBatchSchema, KafkaMessageSchema, SubBatchStatus,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const scheduler=new PromiseScheduler()
const sentinel=new FeedOrderSentinel(10)
const pending=[], completed=[]
let feedCount=0, releaseFirst
let firstFed
const firstFedPromise=new Promise(resolve=>{firstFed=resolve})
let fatal=null
const pipeline={
  async feed(batch,batchContext,budget){
    assert.equal(batch.length,1)
    assert.equal(batch[0].context.message.topic,'flind_wave200_synthetic')
    assert.equal(batch[0].context.message.offset,200)
    assert.equal(batchContext.grpcSeq,1)
    assert.equal(budget.softAt,Infinity)
    feedCount++
    const durability=new Promise(resolve=>{releaseFirst=resolve})
    const done={
      elements:batch.map(entry=>({context:entry.context,result:entry.result})),
      batchContext,sideEffects:[durability],
    }
    if(pending.length)pending.shift()(done)
    else completed.push(done)
    firstFed()
    return {ok:true}
  },
  next(){
    if(completed.length)return Promise.resolve(completed.shift())
    return new Promise(resolve=>pending.push(resolve))
  },
}
const driver=new GrpcStreamIngestDriver(pipeline,scheduler)
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:1,drainTimeoutMs:500,pumpIdleMs:1},
  {driver,feedOrderSentinel:sentinel,onFatal:error=>{fatal=error}},
)
function hello(consumerId){
  return create(IngestStreamRequestSchema,{
    msg:{case:'hello',value:create(StreamHelloSchema,{consumerId,streamEpoch:1n})},
  })
}
function batch(offset,budgetMs){
  return create(IngestStreamRequestSchema,{
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:1n,batchId:'flind-wave200-'+offset,
      messages:[create(KafkaMessageSchema,{
        topic:'flind_wave200_synthetic',partition:0,offset:BigInt(offset),
        timestamp:1761500000000n,key:'flind-synthetic-key-'+offset,
        value:'{"event":"$pageview"}',headers:{},
      })],
      assignmentEpoch:1n,replay:false,softBudgetMs:BigInt(budgetMs),
    })},
  })
}
async function* frames(offset,budgetMs){
  yield hello('flind-wave200-consumer-'+offset)
  yield batch(offset,budgetMs)
}
try{
  await server.start()
  const port=server.server.address().port
  assert.ok(port>0)
  const client=createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+port,httpVersion:'2',
  }))
  const run=async(offset,budgetMs)=>{
    const responseTypes=[],acks=[]
    for await(const reply of client.ingestStream(frames(offset,budgetMs))){
      responseTypes.push(reply.msg.case)
      if(reply.msg.case==='ack')acks.push(reply.msg.value)
    }
    return {responseTypes,acks}
  }
  const firstRun=run(200,0)
  await firstFedPromise
  // feed() resolves asynchronously; only the server's accepted branch
  // updates the actual sentinel. Wait for acceptance, not mere feed entry.
  const acceptanceDeadline=Date.now()+3000
  while(sentinel.size===0 && Date.now()<acceptanceDeadline){
    await new Promise(resolve=>setTimeout(resolve,2))
  }
  assert.equal(feedCount,1)
  assert.equal(sentinel.size,1,'accepted first batch must register')
  // The single capacity slot is held open until first side effect settles,
  // so the second original gRPC stream can only expire before feeding.
  const expired=await run(201,35)
  assert.deepEqual(expired.responseTypes,['ready','ack'])
  assert.equal(expired.acks.length,1)
  assert.equal(expired.acks[0].status,SubBatchStatus.PARTIAL)
  assert.equal(expired.acks[0].accepted,0)
  assert.equal(expired.acks[0].unfinished.length,1)
  assert.equal(expired.acks[0].unfinished[0].offset,201n)
  assert.equal(feedCount,1,'expired batch must never enter actual driver/pipeline')
  assert.equal(sentinel.size,1,
    'an admission-expired/never-fed message must NOT advance actual product order sentinel')
  assert.ok(releaseFirst)
  releaseFirst()
  const first=await firstRun
  assert.equal(first.acks.length,1)
  assert.equal(first.acks[0].status,SubBatchStatus.OK)
  assert.equal(first.acks[0].accepted,1)
  assert.equal(fatal,null)
  process.stdout.write(JSON.stringify({
    phase:'wave200_original_server_accepted_only_order_sentinel',
    original_product_grpc_server_used:true,
    original_production_driver_used:true,
    original_product_feed_order_sentinel_used:true,
    real_http2_protobuf_two_streams:true,
    capacity_one_enforced:true,
    admission_expired_unfed_replayable:true,
    only_fed_messages_advance_order_sentinel:true,
    original_success_ack_after_synthetic_side_effect:true,
    synthetic_pipeline_only:true,
    production_joined_pipeline_qualified:false,
    durable_clickhouse_qualified:false,
    production_rust_consumer_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{
  releaseFirst?.()
  await server.stop()
}
