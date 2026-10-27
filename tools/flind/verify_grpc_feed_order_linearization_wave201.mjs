// Wave201: real Flind original gRPC server/driver/sentinel; synthetic pipeline
// deliberately resolves async feed admission in REVERSE order.
import assert from 'node:assert/strict'
import { create } from '@bufbuild/protobuf'
import { createClient } from '@connectrpc/connect'
import { createGrpcTransport } from '@connectrpc/connect-node'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { GrpcStreamIngestDriver } from './firstparty/nodejs/src/servers/grpc-stream-ingest-driver.ts'
import { PromiseScheduler } from './firstparty/nodejs/src/common/utils/promise-scheduler.ts'
import { FeedOrderSentinel } from './firstparty/nodejs/src/ingestion/api/feed-order-sentinel.ts'
import {
  WorkerIngest, IngestStreamRequestSchema, StreamHelloSchema,
  SubBatchSchema, KafkaMessageSchema, SubBatchStatus,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

const sentinel = new FeedOrderSentinel(10)
const observedChecks = []
const originalCheck = sentinel.check.bind(sentinel)
sentinel.check = (...args) => {
  const result = originalCheck(...args)
  observedChecks.push({
    offset: args[0][0].offset, outOfOrder: result.outOfOrder,
    replayed: result.replayed,
  })
  return result
}
const scheduler = new PromiseScheduler()
const pending = [], completed = []
const submissionOrder = [], admissionCompletionOrder = []
let firstEntered
const firstEnteredPromise = new Promise(resolve => { firstEntered = resolve })
let fatal = null
const pipeline = {
  async feed(batch, batchContext, budget) {
    assert.equal(batch.length, 1)
    const offset = batch[0].context.message.offset
    assert.ok([300, 301].includes(offset))
    assert.equal(batch[0].context.message.topic, 'flind_wave201_synthetic')
    assert.equal(budget.softAt, Infinity)
    submissionOrder.push(offset)
    if (offset === 300) {
      firstEntered()
      // Simulate delayed admission result for the FIRST feed call.
      await new Promise(resolve => setTimeout(resolve, 140))
    }
    admissionCompletionOrder.push(offset)
    const done = {
      elements: batch.map(entry => ({ context: entry.context, result: entry.result })),
      batchContext, sideEffects: [],
    }
    if (pending.length) pending.shift()(done)
    else completed.push(done)
    return {ok:true}
  },
  next() {
    if (completed.length) return Promise.resolve(completed.shift())
    return new Promise(resolve => pending.push(resolve))
  },
}
const driver = new GrpcStreamIngestDriver(pipeline, scheduler)
const server = new WorkerIngestServer(
  {port:0,maxConcurrentBatches:2,pumpIdleMs:1,drainTimeoutMs:400},
  {driver,feedOrderSentinel:sentinel,onFatal:error=>{fatal=error}},
)
function hello() {
  return create(IngestStreamRequestSchema, {
    msg:{case:'hello',value:create(StreamHelloSchema,{
      consumerId:'flind-wave201-same-consumer',streamEpoch:1n,
    })},
  })
}
function batch(offset) {
  return create(IngestStreamRequestSchema, {
    msg:{case:'subBatch',value:create(SubBatchSchema,{
      seq:1n,batchId:'flind-wave201-'+offset,
      messages:[create(KafkaMessageSchema,{
        topic:'flind_wave201_synthetic',partition:0,offset:BigInt(offset),
        timestamp:1761500000000n,key:'flind-wave201-shared-key',
        value:'{"event":"$pageview"}',headers:{},
      })],
      assignmentEpoch:1n,replay:false,softBudgetMs:0n,
    })},
  })
}
async function* frames(offset) {yield hello();yield batch(offset)}
try {
  await server.start()
  const client = createClient(WorkerIngest,createGrpcTransport({
    baseUrl:'http://127.0.0.1:'+server.server.address().port,httpVersion:'2',
  }))
  const run=async offset=>{
    const replies=[]
    for await(const reply of client.ingestStream(frames(offset))) {
      replies.push(reply)
    }
    const acks=replies.filter(x=>x.msg.case==='ack').map(x=>x.msg.value)
    assert.equal(replies[0]?.msg.case,'ready')
    assert.equal(acks.length,1)
    assert.equal(acks[0].status,SubBatchStatus.OK)
    assert.equal(acks[0].accepted,1)
  }
  const slow=run(300)
  await firstEnteredPromise
  const fast=run(301)
  await Promise.all([slow,fast])
  assert.deepEqual(submissionOrder,[300,301],
    'pipeline received lower offset before higher offset')
  assert.deepEqual(admissionCompletionOrder,[301,300],
    'fixture must prove reverse async acceptance completion')
  assert.equal(fatal,null)
  assert.deepEqual(observedChecks.map(x=>x.offset),[300,301],
    'monitor must linearize by the original feed invocation order, not async result order')
  assert.deepEqual(observedChecks.map(x=>x.outOfOrder),[0,0],
    'reversed async completion must not register a false Kafka offset regression')
  assert.equal(sentinel.size,1)
  process.stdout.write(JSON.stringify({
    phase:'wave201_original_grpc_feed_order_linearization',
    real_http2_grpc_two_streams:true,
    original_server_driver_sentinel:true,
    reverse_async_feed_completion_proven:true,
    accepted_only_monitor_checks:true,
    no_false_order_regression:true,
    production_joined_pipeline_qualified:false,
    production_rust_consumer_qualified:false,
    durable_clickhouse_qualified:false,
    release_qualified:false,
  })+'\n')
}finally {await server.stop()}
