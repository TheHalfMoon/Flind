import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'

const pending = []
const completed = []
let feeds = 0
const driver = {
  async feed(streamId, seq, messages, budget) {
    if (messages.length !== 1 || messages[0].topic !== 'flind_wave187_rust_proto' ||
        messages[0].offset !== 187 || messages[0].partition !== 0 ||
        messages[0].value !== '{"uuid":"00000000-0000-4000-8000-000000000187","event":"$pageview"}') {
      return { ok: false, kind: 'before_batch_failed', reason: 'invalid synthetic fixture' }
    }
    feeds++
    const completedBatch = {
      streamId, seq, accepted: 1, unfinished: [], settled: Promise.resolve()
    }
    const waiter = pending.shift()
    if (waiter) waiter(completedBatch)
    else completed.push(completedBatch)
    return { ok: true }
  },
  async next() {
    if (completed.length) return completed.shift()
    return new Promise(resolve => pending.push(resolve))
  },
}
const server = new WorkerIngestServer(
  { port: 0, maxConcurrentBatches: 2, drainTimeoutMs: 300, pumpIdleMs: 1 },
  {driver, onFatal: error => { process.stderr.write('FLIND_NODE_PIPELINE_FATAL\n') }}
)
let finished = false
async function close(){
  if(finished) return
  finished=true
  try { await server.stop() } catch {}
  process.stdout.write(JSON.stringify({ flind_wave187: 'server_stopped', accepted_synthetic_batches: feeds })+'\n')
  process.exit(feeds===1?0:2)
}
process.on('SIGTERM', ()=>{ void close() })
process.on('SIGINT', ()=>{ void close() })
setTimeout(()=>{ void close() }, 45000).unref()
await server.start()
const port=server.server.address().port
process.stdout.write(JSON.stringify({flind_wave187:'listening',port})+'\n')
