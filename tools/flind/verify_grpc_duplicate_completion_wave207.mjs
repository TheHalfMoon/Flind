// Wave207: original Flind production WorkerIngestServer+GrpcStreamIngestDriver.
// A corrupted pipeline that returns one accepted batch twice must not grow
// the admission pool above its configured cap or ACK the same seq twice.
// Real HTTP/2 Connect gRPC / protobuf wire, synthetic pipeline only.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { createClient } from '@connectrpc/connect'
import { createGrpcTransport } from '@connectrpc/connect-node'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import {
  WorkerIngest,IngestStreamRequestSchema,StreamHelloSchema,
  SubBatchSchema,KafkaMessageSchema,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const enqueued=[], pullWaiters=[]
let feeds=0, fatal=null
const pipeline={
  async feed(batch,batchContext,budget){
    const offset=batch[0].context.message.offset
    assert.ok(offset===207 || offset===208)
    assert.equal(budget.softAt,Infinity)
    feeds++
    const complete={elements:batch.map(e=>({context:e.context,result:e.result})),
      batchContext,sideEffects:[]}
    // The pipeline violates its contract by emitting completion of the
    // first batch twice. The server should fail closed, not double grant.
    const results=offset===207?[complete,complete]:[complete]
    for(const item of results){
      if(pullWaiters.length)pullWaiters.shift()(item)
      else enqueued.push(item)
    }
    return {ok:true}
  },
  next(){
    if(enqueued.length)return Promise.resolve(enqueued.shift())
    return new Promise(resolve=>pullWaiters.push(resolve))
  }
}
const server=new WorkerIngestServer({
  port:0,maxConcurrentBatches:2,pumpIdleMs:1,drainTimeoutMs:150,
},{driver:new GrpcStreamIngestDriver(pipeline,new PromiseScheduler()),
   onFatal:error=>{fatal=error}})
function hello(){return create(IngestStreamRequestSchema,{
  msg:{case:'hello',value:create(StreamHelloSchema,{
    consumerId:'flind-wave207-duplicate',streamEpoch:1n,
  })},
})}
function batch(seq,offset){return create(IngestStreamRequestSchema,{
  msg:{case:'subBatch',value:create(SubBatchSchema,{
    seq:BigInt(seq),batchId:'flind-wave207-'+seq,
    assignmentEpoch:1n,replay:false,softBudgetMs:0n,
    messages:[create(KafkaMessageSchema,{
      topic:'flind_wave207_synthetic',partition:0,offset:BigInt(offset),
      timestamp:1761500000000n,key:'flind-wave207-key',
      value:'{"event":"$pageview"}',headers:{},
    })],
  })},
})}
async function* frames(){yield hello();yield batch(1,207);yield batch(2,208)}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const until=async (check,label,limit=1500)=>{
  const end=Date.now()+limit
  while(!check()){if(Date.now()>end)throw Error('timeout '+label);await sleep(3)}
}
try{
  await server.start()
  const client=createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+server.server.address().port,httpVersion:'2',
  }))
  const received=[], errors=[]
  await Promise.race([
    (async()=>{
      try {
        for await(const reply of client.ingestStream(frames())) received.push(reply)
      } catch(error){errors.push(error)}
    })(),
    sleep(1200).then(()=>{throw Error('duplicate test client timed out')}),
  ])
  // Fatal processing may stop the reader before the second buffered frame
  // reaches the driver; only the first accepted batch is required to prove
  // that its duplicate completion must not over-release an admission slot.
  await until(()=>feeds>=1,'first accepted submission')
  await sleep(30)
  const acks=received.filter(x=>x.msg.case==='ack').map(x=>Number(x.msg.value.seq))
  assert.ok(server.slots.available<=2,
    'duplicate completion must not overflow the configured FIFO capacity')
  assert.equal(acks.filter(seq=>seq===1).length<=1,true,
    'duplicate completion must not ACK seq 1 twice')
  assert.ok(fatal instanceof Error,
    'unexpected duplicate completion must poison shared pipeline')
  assert.ok(errors.length>=1,'stream must fail closed after duplicate result')
  process.stdout.write(JSON.stringify({
    phase:'wave207_original_grpc_duplicate_completion_fail_closed',
    original_production_server_driver:true,
    real_http2_grpc_protobuf:true,
    synthetic_duplicate_completion_injected:true,
    no_admission_pool_overrelease:true,
    no_duplicate_ack:true,
    corrupted_pipeline_fails_closed:true,
    production_joined_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    durable_clickhouse_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{await server.stop()}
