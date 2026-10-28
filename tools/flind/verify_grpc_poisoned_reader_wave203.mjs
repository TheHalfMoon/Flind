// Wave203: original production Flind WorkerIngestServer, driver and scheduler.
// The live request iterator must never feed another batch after fatal poison.
// Direct original streaming generator API, synthetic in-memory pipeline.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { Code } from '@connectrpc/connect'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import {
  IngestStreamRequestSchema, StreamHelloSchema, SubBatchSchema, KafkaMessageSchema,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const scheduler=new PromiseScheduler()
let firstFed=null
let fatal=null
const feeds=[], completed=[], pulls=[]
const pipeline={
  async feed(batch,batchContext,budget) {
    const offset=batch[0].context.message.offset
    feeds.push(offset)
    assert.equal(batch.length,1)
    assert.ok(offset===203||offset===204)
    assert.equal(budget.softAt,Infinity)
    if(offset===203){
      const rejected=Promise.reject(new Error('wave203 synthetic disk failure'))
      scheduler.schedule(rejected)
      await rejected.catch(()=>{})
      await Promise.resolve()
    }
    const result={
      elements:batch.map(entry=>({context:entry.context,result:entry.result})),
      batchContext,sideEffects:[],
    }
    if(pulls.length)pulls.shift()(result)
    else completed.push(result)
    firstFed?.()
    return {ok:true}
  },
  next(){
    if(completed.length)return Promise.resolve(completed.shift())
    return new Promise(resolve=>pulls.push(resolve))
  },
}
const driver=new GrpcStreamIngestDriver(pipeline,scheduler)
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,pumpIdleMs:1,drainTimeoutMs:150},
  {driver,onFatal:error=>{fatal=error}},
)
const source={
  frames:[], waiters:[],
  push(frame) {
    if(this.waiters.length) this.waiters.shift()({value:frame,done:false})
    else this.frames.push(frame)
  },
  [Symbol.asyncIterator](){
    return {
      next:()=>this.frames.length
        ? Promise.resolve({value:this.frames.shift(),done:false})
        : new Promise(resolve=>this.waiters.push(resolve)),
    }
  },
}
const hello=create(IngestStreamRequestSchema,{
  msg:{case:'hello',value:create(StreamHelloSchema,{
    consumerId:'flind-wave203-poisoned-reader',streamEpoch:1n,
  })},
})
function batch(seq,offset){
  return create(IngestStreamRequestSchema,{
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:BigInt(seq),batchId:'flind-wave203-'+seq,
      assignmentEpoch:1n,replay:false,softBudgetMs:0n,
      messages:[create(KafkaMessageSchema,{
        topic:'flind_wave203_synthetic',partition:0,offset:BigInt(offset),
        timestamp:1761500000000n,key:'flind-wave203-key',
        value:'{"event":"$pageview"}',headers:{},
      })],
    })},
  })
}
async function until(condition,label,limit=3500){
  const deadline=Date.now()+limit
  while(!condition()){
    if(Date.now()>deadline)throw Error('timeout waiting for '+label)
    await new Promise(resolve=>setTimeout(resolve,3))
  }
}
try{
  await server.start()
  const iter=server.ingestStream(source)[Symbol.asyncIterator]()
  const ready=await iter.next()
  assert.equal(ready.value?.msg.case,'ready')
  source.push(hello)
  source.push(batch(1,203))
  await until(()=>fatal instanceof Error,'original server fatal callback')
  assert.deepEqual(feeds,[203])
  assert.match(fatal.message,/wave203 synthetic disk failure/)
  let streamError=null
  try{ await iter.next() }catch(error){ streamError=error }
  assert.equal(streamError?.code,Code.Internal,'first stream must report fatal')
  source.push(batch(2,204))
  await new Promise(resolve=>setTimeout(resolve,50))
  assert.deepEqual(feeds,[203],
    'poisoned original live request reader must not feed the second batch')
  assert.equal(server.streamCount,0)
  process.stdout.write(JSON.stringify({
    phase:'wave203_original_grpc_poisoned_reader',
    original_server_driver_scheduler:true,
    original_streaming_request_reader:true,
    synthetic_side_effect_rejection_fatal:true,
    first_client_observes_internal_error:true,
    later_inflight_frame_not_fed_after_fatal:true,
    synthetic_pipeline_only:true,
    real_http2_disconnect_qualified:false,
    production_joined_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    durable_clickhouse_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{await server.stop()}
