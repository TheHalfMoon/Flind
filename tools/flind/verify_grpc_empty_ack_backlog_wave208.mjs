// Wave208: original Flind WorkerIngestServer must bound ACK backlog when
// a peer sends many empty sub-batches but never reads their responses.
// Direct production ingestStream iterable with synthetic requests/pipeline;
// no external Kafka/ClickHouse or real HTTP2 transport in this qualifier.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { Code } from '@connectrpc/connect'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import {
 IngestStreamRequestSchema, StreamHelloSchema, SubBatchSchema,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const maxBuffered=256
const frameCount=320
let produced=0, feedCalls=0, fatal=null
const server=new WorkerIngestServer(
 {port:0,maxConcurrentBatches:2,pumpIdleMs:1,drainTimeoutMs:90},
 {driver:{
   async feed(){feedCalls++;return {ok:true}},
   next(){return new Promise(()=>{})},
 },onFatal:e=>{fatal=e}},
)
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const until=async(test,label,deadlineMs=2000)=>{
 const deadline=Date.now()+deadlineMs
 while(!test()){
   if(Date.now()>deadline)throw Error('timed out waiting for '+label)
   await sleep(2)
 }
}
async function* source(){
 yield create(IngestStreamRequestSchema,{msg:{
   case:'hello',value:create(StreamHelloSchema,{consumerId:'flind-wave208-synthetic',streamEpoch:1n}),
 }})
 for(let seq=1;seq<=frameCount;seq++){
   produced++
   yield create(IngestStreamRequestSchema,{msg:{case:'subBatch',
     value:create(SubBatchSchema,{seq:BigInt(seq),batchId:'wave208-'+seq,
       messages:[],assignmentEpoch:1n,replay:false,softBudgetMs:0n})
   }})
 }
}
const stream=server.ingestStream(source())
try{
 await server.start()
 const first=await stream.next()
 assert.equal(first.done,false)
 assert.equal(first.value.msg.case,'ready')
 await until(()=>{
   const state=[...server.streams.values()][0]
   return state?.acks?.done===true
 },'original response backlog to finish or fail')
 const state=[...server.streams.values()][0]
 assert.ok(state)
 const queued=state.acks.items.length
 assert.ok(queued<=maxBuffered,
  'empty-batch ACKs must not grow the original response queue beyond its bound')
 assert.equal(state.acks.error?.code,Code.ResourceExhausted,
  'overflow must fail only the congested stream with resource_exhausted')
 assert.ok(produced<=maxBuffered+1,
  'reader must stop taking new empty frames once responses are backlogged')
 assert.equal(feedCalls,0,'empty batches must never enter pipeline')
 assert.equal(fatal,null,'slow client must not poison shared pipeline')
 let acks=0, caught=null
 try{
  while(true){
   const frame=await stream.next()
   if(frame.done)break
   if(frame.value.msg.case==='ack')acks++
  }
 }catch(error){caught=error}
 assert.equal(caught?.code,Code.ResourceExhausted)
 assert.ok(acks<=maxBuffered)
 assert.equal(server.streamCount,0)
 process.stdout.write(JSON.stringify({
   phase:'wave208_original_grpc_empty_ack_backlog',
   original_product_worker_ingest_server:true,
   no_peer_response_consumption_reproduced:true,
   stream_rejected_at_bounded_ack_capacity:true,
   no_unbounded_empty_batch_queue:true,
   no_pipeline_feed_for_empty_messages:true,
   no_shared_pipeline_fatal:true,
   no_false_success_after_congestion:true,
   source_count:13,
   real_http2_transport_qualified:false,
   original_joined_pipeline_qualified:false,
   production_rust_consumer_qualified:false,
   durable_clickhouse_qualified:false,
   release_qualified:false,
 })+'\n')
}finally{
 try{await stream.return?.()}catch{}
 await server.stop()
}
