// Wave193: real HTTP/2 gRPC + original Flind WorkerIngestServer +
// original Flind GrpcStreamIngestDriver; synthetic in-memory pipeline only.
import assert from 'node:assert/strict'
import {spawnSync} from 'node:child_process'
import { create } from '@bufbuild/protobuf'
import { createClient } from '@connectrpc/connect'
import { createGrpcTransport } from '@connectrpc/connect-node'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import { timeout } from './firstparty/nodejs/src/ingestion/framework/results.ts'
import {
  WorkerIngest, IngestStreamRequestSchema, StreamHelloSchema, SubBatchSchema,
  KafkaMessageSchema, SubBatchStatus,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const binary=process.env.FLIND_WAVE194_CLICKHOUSE_BIN
const state=process.env.FLIND_WAVE194_CLICKHOUSE_STATE
if(!binary?.startsWith('/private/tmp/') || !state?.startsWith('/private/tmp/flind-wave194-wire-')) {
  throw Error('Wave194 only supports scoped pre-approved local disk fixture paths')
}
function sql(query){
  const p=spawnSync(binary,[
    'local','--multiquery','--path',state,
    '--max_memory_usage=134217728','--max_threads=2','--query',query,
  ],{encoding:'utf8',timeout:27000,maxBuffer:100000,stdio:['ignore','pipe','pipe']})
  if(p.error||p.status!==0||p.stdout.length>20000||p.stderr.length>8000){
    throw Error('real ClickHouse MergeTree subprocess failed: '+String(p.stderr).slice(0,300))
  }
  return p.stdout.trim().split('\n').filter(Boolean).map(x=>JSON.parse(x))
}
const uuid='00000000-0000-4000-8000-000000019401'
const pending=[], completed=[], feeds=[]
let failed=null
let releasedAt=0, ackAt=0
const scheduler=new PromiseScheduler()
const pipeline={
  async feed(batch,batchContext,budget){
    assert.equal(batch.length,2)
    assert.equal(batchContext.grpcSeq,1)
    assert.equal(budget.softAt,Infinity)
    for(const [i,entry] of batch.entries()){
      assert.ok(Buffer.isBuffer(entry.context.message.value))
      assert.equal(entry.context.message.offset,100+i)
      assert.equal(entry.context.message.topic,'flind_wave193_synthetic')
      assert.equal(entry.context.message.value.toString(),JSON.stringify({event:'$pageview',index:i}))
    }
    feeds.push({size:batch.length,seq:batchContext.grpcSeq})
    // Test-only ingestion pipeline, but the side effect uses *real* ClickHouse
    // MergeTree disk, closed and independently reopened by another OS process.
    const sideEffect=(async()=>{
      await new Promise(resolve=>setTimeout(resolve,25))
      assert.equal(sql(
        "CREATE TABLE events (uuid UUID,event String,team_id Int64,distinct_id String) "+
        "ENGINE=MergeTree ORDER BY (team_id,uuid);"+
        "INSERT INTO events VALUES ('"+uuid+"','$pageview',101,'flind-synthetic-194');"
      ).length,0)
      const rows=sql("SELECT uuid,event,team_id,distinct_id FROM events "+
        "ORDER BY uuid FORMAT JSONEachRow;")
      assert.equal(rows.length,1)
      assert.equal(rows[0].uuid,uuid)
      assert.equal(rows[0].event,'$pageview')
      assert.equal(rows[0].team_id,101)
      assert.equal(rows[0].distinct_id,'flind-synthetic-194')
      releasedAt=Date.now()
    })()
    const elements=batch.map((entry,i)=>({
      context:entry.context,
      result:i===1 ? timeout('synthetic cutoff') : {type:0},
    }))
    const result={elements,batchContext,sideEffects:[sideEffect]}
    const next=pending.shift()
    if(next)next(result)
    else completed.push(result)
    return {ok:true}
  },
  next(){if(completed.length)return Promise.resolve(completed.shift());return new Promise(resolve=>pending.push(resolve))}
}
const driver=new GrpcStreamIngestDriver(pipeline,scheduler)
const server=new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,drainTimeoutMs:250,pumpIdleMs:1},
  {driver,onFatal:error=>{failed=error}},
)
function hello(){
  return create(IngestStreamRequestSchema,{
    msg:{case:'hello',value:create(StreamHelloSchema,{consumerId:'flind-wave193-original-driver',streamEpoch:1n})},
  })
}
function batch(){
  const messages=[0,1].map(i=>create(KafkaMessageSchema,{
    topic:'flind_wave193_synthetic',partition:0,offset:BigInt(100+i),
    timestamp:1761500000000n,key:'flind:synthetic',
    value:JSON.stringify({event:'$pageview',index:i}),headers:{},
  }))
  return create(IngestStreamRequestSchema,{
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:1n,batchId:'flind-wave193-batch',messages,assignmentEpoch:1n,
      replay:false,softBudgetMs:0n,
    })},
  })
}
async function* frames(){yield hello();yield batch()}
try{
  await server.start()
  const port=server.server.address().port
  assert.ok(Number.isInteger(port)&&port>0)
  const client=createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+port,httpVersion:'2',
  }))
  const responses=[]
  for await(const item of client.ingestStream(frames())){
    responses.push(item)
    if(item.msg.case==='ack')ackAt=Date.now()
  }
  assert.equal(failed,null,'production server must remain healthy')
  assert.equal(feeds.length,1)
  assert.equal(responses[0]?.msg.case,'ready')
  const acks=responses.filter(x=>x.msg.case==='ack').map(x=>x.msg.value)
  assert.equal(acks.length,1)
  assert.equal(acks[0].seq,1n)
  assert.equal(acks[0].status,SubBatchStatus.PARTIAL)
  assert.equal(acks[0].accepted,1)
  assert.equal(acks[0].unfinished.length,1)
  assert.equal(acks[0].unfinished[0].offset,101n)
  assert.ok(releasedAt>0,'test durability gate must really settle')
  assert.ok(ackAt>=releasedAt,'original server ACK must follow production driver settlement')
  process.stdout.write(JSON.stringify({
    phase:'wave194_original_production_driver_durable_mergetree_wire',
    original_grpc_server_used:true,
    original_grpc_driver_used:true,
    real_http2_proto_stream_pass:true,
    no_early_ack_before_side_effects:true,
    timed_out_offset_replayable:true,
    clickhouse_mergetree_disk_readback_pass:releasedAt>0,
    synthetic_persisted_event_count:1,
    accepted:acks[0].accepted,
    unfinished:acks[0].unfinished.length,
    production_joined_pipeline_qualified:false,
    durable_clickhouse_qualified:false,
    production_clickhouse_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    release_qualified:false,
  })+'\n')
}finally{await server.stop()}
