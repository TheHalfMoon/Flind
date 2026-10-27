import assert from 'node:assert/strict'
import { WorkerIngestServer } from './firstparty/nodejs/src/ingestion/api/grpc-server.ts'
import { create } from '@bufbuild/protobuf'
import { Code, createClient } from '@connectrpc/connect'
import { createGrpcTransport } from '@connectrpc/connect-node'
import {
    WorkerIngest, IngestStreamRequestSchema, StreamHelloSchema, SubBatchSchema,
    KafkaMessageSchema, SubBatchStatus,
} from './firstparty/nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts'

let passed = 0
let responses = []
let feeds = []
let pending = []
let finished = []
const driver = {
    async feed(streamId, seq, messages, budget) {
        feeds.push({streamId, seq, messages, budget})
        setTimeout(() => {
            const entry = {streamId, seq, accepted: messages.length, unfinished: [], settled: Promise.resolve()}
            if (pending.length) pending.shift()(entry)
            else finished.push(entry)
        }, 5)
        return {ok:true}
    },
    async next() {
        if (finished.length) return finished.shift()
        return new Promise(resolve => pending.push(resolve))
    }
}
const server = new WorkerIngestServer(
    {port: 0, maxConcurrentBatches:2, drainTimeoutMs:200},
    {driver, onFatal: e=>{throw e}},
)
await server.start()
const port = server.server.address().port
assert.ok(Number.isInteger(port) && port > 0)
passed++
const transport = createGrpcTransport({
    baseUrl: 'http://127.0.0.1:' + port,
    httpVersion: '2',
})
const client = createClient(WorkerIngest, transport)
function hello() {
    return create(IngestStreamRequestSchema, {
        msg:{case:'hello',value:create(StreamHelloSchema,{consumerId:'flind-wave186-synthetic',streamEpoch:1n})},
    })
}
function batch(seq, offset) {
    const message=create(KafkaMessageSchema,{
        topic:'flind_wave186_synthetic',
        partition:0,offset:BigInt(offset),timestamp:1761500000000n,
        key:'flind:synthetic',value:'{"event":"$pageview"}',headers:{},
    })
    return create(IngestStreamRequestSchema,{
        msg:{case:'subBatch',value:create(SubBatchSchema,{
            seq:BigInt(seq),batchId:'flind-wave186-batch',messages:[message],
            assignmentEpoch:1n,replay:false,softBudgetMs:0n,
        })},
    })
}
async function* validFrames(){
    yield hello()
    yield batch(1,42)
}
const got=[]
for await (const reply of client.ingestStream(validFrames())){
    got.push(reply)
}
assert.equal(got[0]?.msg.case,'ready')
const acks=got.filter(x=>x.msg.case==='ack').map(x=>x.msg.value)
assert.equal(acks.length,1)
assert.equal(acks[0].seq,1n)
assert.equal(acks[0].status,SubBatchStatus.OK)
assert.equal(acks[0].accepted,1)
assert.equal(feeds[0].messages[0].offset,42)
passed+=6
const startFeeds=feeds.length
async function* invalidFrames(){
    yield hello()
    yield batch(2,91)
}
let rejected=null
try { for await(const _ of client.ingestStream(invalidFrames())){} }
catch (err) {rejected=err}
assert.ok(rejected,'missing sequence must be rejected')
assert.equal(rejected.code, Code.FailedPrecondition)
assert.equal(feeds.length,startFeeds)
passed+=3
// The real protobuf/grpc path must fail closed rather than rounding Kafka
// bigint offset to a different record's safely representable position.
async function* unsafeOffsetFrames(){
    yield hello()
    yield batch(1,9007199254740993n)
}
let badOffset=null
try {for await(const _ of client.ingestStream(unsafeOffsetFrames())){}}
catch(err){badOffset=err}
assert.ok(badOffset,'unsafe Kafka offset must terminate gRPC stream')
assert.equal(feeds.length,startFeeds)
passed+=2
// The empty batch is a protocol-successful no-op: ACK without entering the
// pipeline (otherwise it could wait forever for a nonexistent completion).
async function* emptyBatchFrames(){
    yield hello()
    yield create(IngestStreamRequestSchema,{
        msg:{case:'subBatch',value:create(SubBatchSchema,{
            seq:1n,batchId:'flind-wave186-empty',messages:[],softBudgetMs:0n,
        })},
    })
}
const emptyResponses=[]
for await (const response of client.ingestStream(emptyBatchFrames())) emptyResponses.push(response)
const emptyAcks=emptyResponses.filter(x=>x.msg.case==='ack')
assert.equal(emptyResponses[0]?.msg.case,'ready')
assert.equal(emptyAcks.length,1)
assert.equal(emptyAcks[0].msg.value.accepted,0)
assert.equal(emptyAcks[0].msg.value.status,SubBatchStatus.OK)
assert.equal(feeds.length,startFeeds)
passed+=5
async function* duplicateHelloFrames(){
    yield hello()
    yield hello()
}
let duplicate=null
try{for await (const _ of client.ingestStream(duplicateHelloFrames())){}}
catch(err){duplicate=err}
assert.ok(duplicate)
assert.equal(duplicate.code,Code.FailedPrecondition)
assert.equal(feeds.length,startFeeds)
passed+=3
await server.stop()
process.stdout.write(JSON.stringify({
    phase:'first_party_grpc_server_real_http2_wire',
    actual_first_party_grpc_server_started:true,
    real_grpc_http2_handshake_and_ack:true,
    unsafe_sequence_rejected:true,
    assertions_passed:passed,
    first_party_node_worker_pipeline_qualified:false,
    first_party_rust_to_node_qualified:false,
    durable_clickhouse_qualified:false,
    authenticated_tenant_isolation_qualified:false,
    release_qualified:false,
})+'\n')
