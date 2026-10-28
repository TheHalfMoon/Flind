// Wave206: original production Flind server and driver, actual HTTP/2/Protobuf.
// Infinite at_capacity retries must stop if the consumer cancels an unlimited
// budget sub-batch. All work is synthetic/in-memory, no real Kafka/ClickHouse.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { createClient } from '@connectrpc/connect'
import { createGrpcTransport } from '@connectrpc/connect-node'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import { WorkerIngest,IngestStreamRequestSchema,StreamHelloSchema,SubBatchSchema,KafkaMessageSchema } from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

let retryCalls=0, fatal=null
const pipeline={
  async feed(batch,context,budget){
    assert.equal(batch.length,1)
    assert.equal(batch[0].context.message.offset,206)
    assert.equal(budget.softAt,Infinity)
    retryCalls++
    return {ok:false,kind:'at_capacity',reason:'synthetic pipeline saturated'}
  },
  next(){return new Promise(()=>{})},
}
const server=new WorkerIngestServer({
  port:0,maxConcurrentBatches:1,capacityRetryMs:5,pumpIdleMs:1,drainTimeoutMs:150,
},{driver:new GrpcStreamIngestDriver(pipeline,new PromiseScheduler()),onFatal:err=>{fatal=err}})
const abort=new AbortController()
const until=async (condition,label,timeout=3000)=>{
  const deadline=Date.now()+timeout
  while(!condition()){
    if(Date.now()>deadline)throw Error('timeout waiting for '+label)
    await new Promise(resolve=>setTimeout(resolve,5))
  }
}
async function* frames(){
  yield create(IngestStreamRequestSchema,{msg:{case:'hello',value:create(StreamHelloSchema,{
    consumerId:'flind-wave206-cancelled',streamEpoch:1n,
  })}})
  yield create(IngestStreamRequestSchema,{msg:{case:'subBatch',value:create(SubBatchSchema,{
    seq:1n,batchId:'flind-wave206-cancelled-unlimited',
    assignmentEpoch:1n,replay:false,softBudgetMs:0n,
    messages:[create(KafkaMessageSchema,{
      topic:'flind_wave206_synthetic',partition:0,offset:206n,
      timestamp:1761500000000n,key:'synthetic',
      value:'{"event":"$pageview"}',headers:{},
    })],
  })}})
}
try{
  await server.start()
  const client=createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+server.server.address().port,httpVersion:'2',
  }))
  const received=[]
  const result=(async()=>{
    try{
      for await(const reply of client.ingestStream(frames(),{signal:abort.signal})){
        received.push(reply.msg.case)
      }
    }catch(error){
      if(!abort.signal.aborted)throw error
    }
  })()
  await until(()=>retryCalls>=3,'original pipeline capacity retries')
  assert.equal(server.slots.available,0,'one granted slot held during capacity retry')
  assert.equal(fatal,null)
  abort.abort()
  await Promise.race([result,new Promise((_,reject)=>setTimeout(()=>reject(Error('client cancel timed out')),1500))])
  await until(()=>server.slots.available===1,'cancelled stream releases FIFO slot',1500)
  const countAfterCancel=retryCalls
  await new Promise(resolve=>setTimeout(resolve,55))
  assert.equal(retryCalls,countAfterCancel,'no pipeline feed after client disconnect')
  assert.equal(server.acceptedBatches.size,0,'no phantom accepted metrics')
  assert.equal(fatal,null)
  assert.equal(received.includes('ack'),false,'cancelled unaccepted batch must not be acked')
  process.stdout.write(JSON.stringify({
    phase:'wave206_original_grpc_cancel_during_capacity_retry',
    real_http2_protobuf_client:true,
    original_server_and_driver:true,
    infinite_budget_at_capacity_reproduced:true,
    client_cancel_releases_admission_slot:true,
    retry_loop_stops_after_cancel:true,
    no_phantom_accepted_batch:true,
    no_false_ack:true,
    production_joined_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    durable_clickhouse_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{
  abort.abort()
  await server.stop()
}
