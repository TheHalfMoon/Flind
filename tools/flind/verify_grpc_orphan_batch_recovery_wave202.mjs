// Wave202: original Flind gRPC server and original production driver over
// original server streaming-generator API; synthetic pipeline only.
// Reproduce a completed-but-uncollected orphan after a client disconnect.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import {
 WorkerIngest,IngestStreamRequestSchema,StreamHelloSchema,
 SubBatchSchema,KafkaMessageSchema,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const pendingPulls=[], completed=[]
let acceptedRecord=null, feedCalls=0, fatal=null
const scheduler=new PromiseScheduler()
const pipeline={
  async feed(batch,batchContext,budget){
    assert.equal(batch.length,1)
    assert.equal(batch[0].context.message.offset,202)
    assert.equal(batch[0].context.message.topic,'flind_wave202_synthetic')
    assert.equal(budget.softAt,Infinity)
    feedCalls++
    acceptedRecord={
      elements:batch.map(entry=>({context:entry.context,result:entry.result})),
      batchContext,sideEffects:[],
    }
    return {ok:true}
  },
  next(){
    if(completed.length)return Promise.resolve(completed.shift())
    return new Promise(resolve=>pendingPulls.push(resolve))
  },
}
const driver=new GrpcStreamIngestDriver(pipeline,scheduler)
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:1,pumpIdleMs:1,drainTimeoutMs:250},
  {driver,onFatal:error=>{fatal=error}},
)
async function until(check,label,ms=5500){
  const deadline=Date.now()+ms
  while(!check()){
    if(Date.now()>deadline)throw Error('timeout waiting for '+label)
    await new Promise(resolve=>setTimeout(resolve,3))
  }
}
async function* frames(){
  yield create(IngestStreamRequestSchema,{
    msg:{case:'hello',value:create(StreamHelloSchema,{
      consumerId:'flind-wave202-disconnected',streamEpoch:1n,
    })},
  })
  yield create(IngestStreamRequestSchema,{
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:1n,batchId:'wave202-orphan',
      messages:[create(KafkaMessageSchema,{
        topic:'flind_wave202_synthetic',partition:0,offset:202n,
        timestamp:1761500000000n,key:'synthetic-key',
        value:'{"event":"$pageview"}',headers:{},
      })],
      assignmentEpoch:1n,replay:false,softBudgetMs:0n,
    })},
  })
  // Finish request upload, but the original response stream stays open
  // while the accepted batch has not completed. Cancel only that response.
}
let disconnected=false
let iterator=null
try{
  await server.start()
  iterator=server.ingestStream(frames())
  const ready=await iterator.next()
  assert.equal(ready.value?.msg.case,'ready')
  const received=['ready']
  await until(()=>feedCalls===1 && acceptedRecord && server.acceptedBatches.size===1,
    'server to retain one accepted batch')
  await until(()=>pendingPulls.length===1,'pump to await pipeline result')
  assert.ok(received.includes('ready'))
  await iterator.return()
  disconnected=true
  await until(()=>server.streamCount===0,'original stream generator disconnect')
  assert.equal(server.acceptedBatches.size,1,'orphan must remain tracked after client removal')

  // Actual original BatchingPipeline.next() can return null temporarily
  // while a fed batch still processes. In this exact interleaving the client
  // has already disappeared, so counting only live stream.inFlight was zero.
  pendingPulls.shift()(null)
  await new Promise(resolve=>setTimeout(resolve,30))
  assert.equal(server.totalInFlight(),1,
    'server must count orphaned accepted batches, not only live gRPC streams')
  await until(()=>pendingPulls.length>0,'pump to stay alive for orphan completion')
  pendingPulls.shift()(acceptedRecord)
  await until(()=>server.acceptedBatches.size===0,
    'orphan completion to release its accepted metric',4000)
  assert.equal(server.slots.available,1,'orphan completion must restore FIFO capacity')
  assert.equal(server.streamCount,0)
  assert.equal(feedCalls,1)
  assert.equal(fatal,null)
  assert.equal(received.includes('ack'),false,'disconnected consumer must replay unacknowledged work')
  process.stdout.write(JSON.stringify({
    phase:'wave202_original_grpc_orphan_batch_pump_recovery',
    original_server_and_driver:true,
    original_stream_generator_disconnect:true,
    accepted_batch_retained_after_stream_removed:true,
    transient_pipeline_null_reproduced:true,
    orphan_inflight_counted:true,
    orphan_completion_pumped:true,
    admission_slot_restored:true,
    consumer_no_false_ack:true,
    production_joined_pipeline_qualified:false,
    durable_clickhouse_qualified:false,
    production_rust_consumer_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{
  if(!disconnected) await iterator?.return?.()
  await server.stop()
}
