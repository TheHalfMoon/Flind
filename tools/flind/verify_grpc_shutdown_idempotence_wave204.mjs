// Wave204: actual original WorkerIngestServer and production driver.
// Focus: concurrent and repeated shutdown must safely return without throwing.
import assert from 'node:assert/strict'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'

const pipeline={
  feed:async()=>({ok:true}),
  next:()=>new Promise(()=>{}),
}
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,pumpIdleMs:1,drainTimeoutMs:100},
  {driver:new GrpcStreamIngestDriver(pipeline,new PromiseScheduler()),onFatal:()=>{}},
)
const timeout=(promise, label)=>Promise.race([
  promise,
  new Promise((_,reject)=>setTimeout(()=>reject(Error(label+' timeout')),4000)),
])
try{
  await server.start()
  assert.ok(server.server?.listening,'server must start')
  await timeout(Promise.all([server.stop(),server.stop()]),'concurrent stop')
  assert.equal(server.server,null)
  await timeout(server.stop(),'repeated stop')
  assert.equal(server.streamCount,0)
  process.stdout.write(JSON.stringify({
    phase:'wave204_original_server_shutdown_idempotence',
    original_product_server:true,
    original_product_driver:true,
    concurrent_stop_passes:true,
    repeated_stop_passes:true,
    no_network_client:true,
    synthetic_pipeline_only:true,
    production_joined_pipeline_qualified:false,
    durable_clickhouse_qualified:false,
    production_rust_consumer_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{
  try{await timeout(server.stop(),'final stop')}catch{}
}
