// Actual original Flind WorkerIngestServer + test-only durable MergeTree driver.
// Never use this fixture as the production StreamIngestDriver.
import { spawnSync } from 'node:child_process'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
const binary=process.env.FLIND_WAVE190_CLICKHOUSE_BIN
const scratch=process.env.FLIND_WAVE190_CLICKHOUSE_STATE
if (!binary?.startsWith('/private/tmp/') || !scratch?.startsWith('/private/tmp/')) {
  throw Error('Wave190 only supports marked local fixture paths')
}
const expected=[
  '{"distinct_id":"user-one","event":"$pageview","properties":{"$pathname":"/home"},"team_id":101}',
  '{"distinct_id":"user-one","event":"$pageview","properties":{"$pathname":"/private"},"team_id":202}',
  '{"distinct_id":"user-one","event":"purchase","properties":{"$pathname":"/pricing"},"team_id":101}',
]
const uuid=i=>'00000000-0000-4000-8000-'+String(19001+i).padStart(12,'0')
let feeds=0, verified=false
const pending=[],finished=[]
function sql(query) {
  const p=spawnSync(binary,['local','--multiquery','--path',scratch,
    '--max_memory_usage=134217728','--max_threads=2','--query',query],
    {encoding:'utf8',timeout:27000,maxBuffer:100000,stdio:['ignore','pipe','pipe']})
  if(p.error || p.status!==0 || p.stdout.length>20000 || p.stderr.length>8000){
    throw Error('synthetic durable ClickHouse subprocess failed')
  }
  return p.stdout.trim().split('\n').filter(Boolean).map(x=>JSON.parse(x))
}
const driver={
  async feed(streamId,seq,messages,budget){
    if (feeds!==0 || seq!==1n && seq!==1 || messages.length!==3 ||
      messages.some((m,i)=>m.value!==expected[i] || m.offset!==i
         || m.partition!==0 || m.topic!=='flind_wave179_synthetic_only')) {
      return {ok:false,kind:'before_batch_failed',reason:'unapproved synthetic batch'}
    }
    feeds++
    const cells=expected.map((v,i)=>{
      const event=JSON.parse(v)
      return "('"+uuid(i)+"','"+event.event+"','"+JSON.stringify(event.properties).replaceAll("'","''")+"','2026-10-27 12:10:0"+i+
        ".000000',"+event.team_id+",'"+event.distinct_id+"')"
    }).join(',')
    const start=sql("CREATE TABLE events (uuid UUID,event String,properties String,"+
      "timestamp DateTime64(6,'UTC'),team_id Int64,distinct_id String) "+
      "ENGINE=MergeTree ORDER BY (team_id,timestamp,uuid);"+
      "INSERT INTO events VALUES "+cells+";")
    if(start.length!==0)throw Error('unexpected ClickHouse insert response')
    // A new ClickHouse OS process opens the on-disk MergeTree state.
    const rows=sql('SELECT uuid,team_id,event,properties,distinct_id FROM events ORDER BY uuid FORMAT JSONEachRow;')
    if (rows.length!==3 || rows.some((row,i)=>{
      const event=JSON.parse(expected[i])
      return row.uuid!==uuid(i)||row.team_id!==event.team_id||row.event!==event.event||
        row.properties!==JSON.stringify(event.properties)||row.distinct_id!==event.distinct_id
    }))throw Error('durable Kafka event UUID readback failed')
    verified=true
    const ack={streamId,seq,accepted:3,unfinished:[],settled:Promise.resolve()}
    const resolve=pending.shift()
    if(resolve)resolve(ack)
    else finished.push(ack)
    return {ok:true}
  },
  async next(){
    if(finished.length)return finished.shift()
    return new Promise(resolve=>pending.push(resolve))
  }
}
const server=new WorkerIngestServer(
 {port:0,maxConcurrentBatches:2,drainTimeoutMs:400,pumpIdleMs:1},
 {driver,onFatal:()=>process.stderr.write('FLIND_WAVE190_SYNTHETIC_DRIVER_FATAL\n')}
)
let done=false
async function stop(){
 if(done)return
 done=true
 try{await server.stop()}catch{}
 process.stdout.write(JSON.stringify({phase:'wave190_stopped',
   durable_three_reopened:verified,accepted_batches:feeds})+'\n')
 process.exit(verified&&feeds===1?0:2)
}
process.on('SIGTERM',()=>void stop())
setTimeout(()=>void stop(),70000).unref()
await server.start()
process.stdout.write(JSON.stringify({phase:'wave190_listening',port:server.server.address().port})+'\n')
