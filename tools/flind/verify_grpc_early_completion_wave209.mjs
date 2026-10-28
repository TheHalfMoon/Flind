// Wave209: a valid original production gRPC pipeline may publish a completed
// batch before async feed() resolves acceptance to the reader. Never poison
// the server merely because another stream woke the pump in that interval.
// Original Flind WorkerIngestServer/driver/scheduler, real local HTTP/2 gRPC.
// Pipeline remains an explicitly synthetic injected test double.
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

let arrivedFirst
const firstSubmitted=new Promise(resolve=>{arrivedFirst=resolve})
let delayFirstRelease
const firstRelease=new Promise(resolve=>{delayFirstRelease=resolve})
let firstWasPublished=false, secondWasAccepted=false, fatal=null
const queued=[], waiters=[]
const attempts=[]
const pipeline={
 async feed(batch,batchContext,budget){
  const offset=batch[0].context.message.offset
  assert.ok([209,210].includes(offset))
  assert.equal(budget.softAt,Infinity)
  attempts.push(offset)
  const result={
   elements:batch.map(entry=>({context:entry.context,result:entry.result})),
   batchContext,sideEffects:[],
  }
  if(waiters.length) waiters.shift()(result)
  else queued.push(result)
  if(offset===209){
   firstWasPublished=true
   arrivedFirst()
   await firstRelease
  }else {
   secondWasAccepted=true
  }
  return {ok:true}
 },
 next(){
  if(queued.length)return Promise.resolve(queued.shift())
  return new Promise(resolve=>waiters.push(resolve))
 },
}
const sentinel=new FeedOrderSentinel(10)
const scheduler=new PromiseScheduler()
const server=new WorkerIngestServer(
 {port:0,maxConcurrentBatches:2,pumpIdleMs:1,drainTimeoutMs:450},
 {driver:new GrpcStreamIngestDriver(pipeline,scheduler),
  feedOrderSentinel:sentinel,onFatal:error=>{fatal=error}},
)
function hello(offset){return create(IngestStreamRequestSchema,{msg:{
 case:'hello',value:create(StreamHelloSchema,{
 consumerId:'flind-wave209-early-'+offset,streamEpoch:1n,
 }),
}})}
function batch(offset){return create(IngestStreamRequestSchema,{msg:{
 case:'subBatch',value:create(SubBatchSchema,{
 seq:1n,batchId:'wave209-'+offset,assignmentEpoch:1n,replay:false,
 softBudgetMs:0n,
 messages:[create(KafkaMessageSchema,{
  topic:'flind_wave209_synthetic',partition:0,offset:BigInt(offset),
  timestamp:1761500000000n,key:'wave209-'+offset,
  value:'{"event":"$pageview"}',headers:{},
 })],
 }),
}})}
async function* frames(offset){yield hello(offset);yield batch(offset)}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
async function bounded(task,ms){
 return await Promise.race([task,sleep(ms).then(()=>{throw Error('gRPC acknowledgement timed out')})])
}
try{
 await server.start()
 const client=createClient(WorkerIngest,createGrpcTransport({
  baseUrl:'http://127.0.0.1:'+server.server.address().port,httpVersion:'2',
 }))
 const run=async offset=>{
  const output=[]
  for await(const reply of client.ingestStream(frames(offset)))output.push(reply)
  const acks=output.filter(x=>x.msg.case==='ack').map(x=>x.msg.value)
  assert.equal(output[0]?.msg.case,'ready')
  assert.equal(acks.length,1)
  assert.equal(acks[0].status,SubBatchStatus.OK)
  assert.equal(acks[0].accepted,1)
 }
 const slow=run(209)
 await firstSubmitted
 const fast=run(210)
 // The second accepted submission wakes the original pump while the
 // first completion is already available but its feed() is still pending.
 const poll=async()=>{
  const end=Date.now()+900
  while(!secondWasAccepted){if(Date.now()>end)throw Error('second feed not accepted');await sleep(3)}
 }
 await poll()
 await sleep(25)
 assert.equal(firstWasPublished,true)
 delayFirstRelease()
 await bounded(Promise.all([slow,fast]),1200)
 assert.deepEqual(attempts,[209,210])
 assert.equal(fatal,null,'valid early pipeline completion must not poison the shared ingestion server')
 assert.equal(server.slots.available,2,'both accepted slots must settle exactly once')
 assert.equal(sentinel.size,2)
 process.stdout.write(JSON.stringify({
  phase:'wave209_original_grpc_early_completion_before_admission',
  original_production_server_and_driver:true,
  real_http2_two_streams:true,
  first_completion_before_feed_promise:true,
  independent_second_admission_wakes_pump:true,
  early_completion_acks_after_acceptance:true,
  no_false_pipeline_fatal:true,
  no_capacity_leak:true,
  synthetic_pipeline_only:true,
  production_joined_pipeline_qualified:false,
  production_rust_consumer_qualified:false,
  durable_clickhouse_qualified:false,
  release_qualified:false,
 })+'\n')
}finally{
 delayFirstRelease()
 await server.stop()
}
