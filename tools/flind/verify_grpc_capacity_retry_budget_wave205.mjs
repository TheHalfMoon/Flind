// Wave205: original Flind gRPC server and production driver, live HTTP/2.
// The synthetic pipeline deliberately returns at_capacity until the first
// sub-batch's finite soft budget expires; unfed messages must be replayable.
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

let retries=0, followupFeeds=0, fatal=null
const seenOffsets=[]
const sentinel=new FeedOrderSentinel(10)
const originalCheck=sentinel.check.bind(sentinel)
sentinel.check=(messages,...args)=>{
  seenOffsets.push(messages[0].offset)
  return originalCheck(messages,...args)
}
const scheduler=new PromiseScheduler()
const pending=[],completed=[]
const pipeline={
  async feed(batch,batchContext,budget){
    assert.equal(batch.length,1)
    const offset=batch[0].context.message.offset
    assert.ok([205,206].includes(offset))
    assert.equal(batch[0].context.message.topic,'flind_wave205_synthetic')
    if(offset===205){
      retries++
      return {ok:false,kind:'at_capacity',reason:'synthetic pipeline capacity drift'}
    }
    followupFeeds++
    const result={
      elements:batch.map(entry=>({context:entry.context,result:entry.result})),
      batchContext,sideEffects:[],
    }
    if(pending.length)pending.shift()(result)
    else completed.push(result)
    return {ok:true}
  },
  next(){
    if(completed.length)return Promise.resolve(completed.shift())
    return new Promise(resolve=>pending.push(resolve))
  },
}
const driver=new GrpcStreamIngestDriver(pipeline,scheduler)
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,capacityRetryMs:3,pumpIdleMs:2,drainTimeoutMs:200},
  {driver,feedOrderSentinel:sentinel,onFatal:error=>{fatal=error}},
)
const hello=create(IngestStreamRequestSchema,{
  msg:{case:'hello',value:create(StreamHelloSchema,{
    consumerId:'flind-wave205-consumer',streamEpoch:1n,
  })},
})
function batch(seq,offset,softBudgetMs){
  return create(IngestStreamRequestSchema,{
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:BigInt(seq),batchId:'flind-wave205-'+seq,
      messages:[create(KafkaMessageSchema,{
        topic:'flind_wave205_synthetic',partition:4,offset:BigInt(offset),
        timestamp:1761500000000n,key:'wave205-shared-key',
        value:'{"event":"$pageview"}',headers:{},
      })],
      assignmentEpoch:1n,replay:false,softBudgetMs:BigInt(softBudgetMs),
    })},
  })
}
async function* frames(){
  yield hello
  yield batch(1,205,40)
  yield batch(2,206,0)
}
const timeout=(ms,label)=>new Promise((_,reject)=>
  setTimeout(()=>reject(new Error(label+' timed out after '+ms+'ms')),ms)
)
try{
  await server.start()
  const client=createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+server.server.address().port,httpVersion:'2',
  }))
  const replies=await Promise.race([
    (async()=>{
      const out=[]
      for await(const reply of client.ingestStream(frames()))out.push(reply)
      return out
    })(),
    timeout(800,'capacity retry soft budget'),
  ])
  const acks=replies.filter(x=>x.msg.case==='ack').map(x=>x.msg.value)
  assert.equal(replies[0]?.msg.case,'ready')
  assert.equal(acks.length,2)
  assert.deepEqual(acks.map(x=>Number(x.seq)),[1,2])
  assert.equal(acks[0].status,SubBatchStatus.PARTIAL)
  assert.equal(acks[0].accepted,0)
  assert.deepEqual(acks[0].unfinished.map(x=>[x.partition,Number(x.offset)]),[[4,205]])
  assert.equal(acks[1].status,SubBatchStatus.OK)
  assert.equal(acks[1].accepted,1)
  assert.ok(retries>=1)
  assert.equal(followupFeeds,1)
  assert.deepEqual(seenOffsets,[206],'rejected capacity retries must not alter accepted feed-order watermark')
  assert.equal(sentinel.size,1)
  assert.equal(fatal,null)
  assert.equal(server.slots.available,2,'capacity retries must return the acquired FIFO slot')
  process.stdout.write(JSON.stringify({
    phase:'wave205_original_grpc_capacity_retry_budget',
    real_http2_protobuf_roundtrip:true,
    original_server_driver_and_sentinel:true,
    pipeline_at_capacity_retried:true,
    finite_budget_unfed_partial_replayable:true,
    subsequent_batch_accepted_and_acked:true,
    no_order_monitor_pollution:true,
    no_admission_slot_leak:true,
    production_joined_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    durable_clickhouse_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{await server.stop()}
