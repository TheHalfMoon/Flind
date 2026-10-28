// Wave204: actual original Flind WorkerIngestServer with real HTTP/2 TCP client.
// An idle, unfinished HTTP/2 request must not hang shutdown after drain.
import assert from 'node:assert/strict'
import http2 from 'node:http2'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
const pipeline={
  feed:async()=>({ok:true}),
  next:()=>new Promise(()=>{}),
}
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,pumpIdleMs:1,drainTimeoutMs:120},
  {driver:new GrpcStreamIngestDriver(pipeline,new PromiseScheduler()),onFatal:()=>{}},
)
let client=null,request=null,stopPromise=null
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const until=async(fn,label,ms=1200)=>{
  const deadline=Date.now()+ms
  while(!fn()){
    if(Date.now()>deadline)throw new Error('timeout waiting for '+label)
    await sleep(5)
  }
}
try {
  await server.start()
  assert.ok(server.server?.listening)
  const port=server.server.address().port
  client=http2.connect('http://127.0.0.1:'+port)
  client.on('error',()=>{})
  request=client.request({
    ':method':'POST',
    ':path':'/ingestion.worker.v1.WorkerIngest/IngestStream',
    'content-type':'application/grpc',
    'te':'trailers',
  })
  request.on('error',()=>{})
  request.on('data',()=>{})
  // Crucially never call request.end(): a slow/idle peer can keep the
  // HTTP/2 stream active after the server starts its drain.
  await until(()=>server.sessions.size===1,'registered real HTTP2 session')
  assert.equal(server.acceptedBatches.size,0,'no accepted work must block shutdown')
  const begun=Date.now()
  let finished=false
  stopPromise=server.stop().then(()=>{finished=true})
  await Promise.race([
    stopPromise,
    sleep(1500).then(()=>{if(!finished)throw new Error('original stop() hung on idle unfinished HTTP2 request')}),
  ])
  assert.equal(server.server,null)
  assert.ok(Date.now()-begun<1500,'shutdown must bound idle peer wait')
  process.stdout.write(JSON.stringify({
    phase:'wave204_original_http2_idle_shutdown',
    original_product_grpc_server:true,
    original_product_driver:true,
    real_node_http2_tcp_session:true,
    unfinished_idle_client_request:true,
    shutdown_completed_within_1500ms:true,
    no_durable_batch_present:true,
    production_joined_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    durable_clickhouse_qualified:false,
    release_qualified:false,
  })+'\n')
} finally {
  try{request?.close()}catch{}
  try{client?.destroy()}catch{}
  for(const session of server.sessions){try{session.destroy()}catch{}}
  if(stopPromise) await Promise.race([stopPromise.catch(()=>{}),sleep(1000)])
}
