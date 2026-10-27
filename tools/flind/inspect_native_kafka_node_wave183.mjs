// Wave183: apply actual first-party TypeScript deserializer to a Kafka event
// consumed from the same native Rust Capture HTTP ACK UUID. Synthetic only.
// No gRPC worker or production ingestion engine is invoked.
import { deserializeKafkaMessage } from '../../nodejs/src/ingestion/api/kafka-message-converter.ts'

const MAX = 64 * 1024
let received = ''
for await (const part of process.stdin) {
    received += part.toString('utf8')
    if (Buffer.byteLength(received) > MAX) {
        process.stderr.write('flind synthetic record too large\n')
        process.exit(2)
    }
}
const fail = () => {
    process.stderr.write('flind synthetic native Kafka event invalid\n')
    process.exit(2)
}

let input
try {
    input = JSON.parse(received)
} catch {
    fail()
}
if (typeof input !== 'object' || !input
    || input.topic !== 'flind_wave180_first_party_native_capture'
    || typeof input.uuid !== 'string' || !/^[0-9a-f-]{36}$/i.test(input.uuid)
    || typeof input.event !== 'object' || !input.event
    || input.event.uuid !== input.uuid
    || input.event.event !== '$pageview'
    || input.event.distinct_id !== 'flind-wave112-synthetic'
    || input.event.token !== 'flind_synthetic_internal_token'
    || Object.hasOwn(input.event, 'team_id')) {
    fail()
}
const source = JSON.stringify(input.event)
const msg = deserializeKafkaMessage({
    topic: input.topic,
    partition: 0,
    offset: 0,
    timestamp: 0,
    key: null,
    value: source,
    headers: {},
})
let parsed
try {
    parsed = JSON.parse(msg.value?.toString('utf8') ?? '')
} catch {
    fail()
}
if (msg.topic !== input.topic || !Buffer.isBuffer(msg.value)
    || msg.size !== Buffer.byteLength(source, 'utf8') || msg.key !== undefined
    || parsed.uuid !== input.uuid || parsed.event !== '$pageview'
    || parsed.token !== 'flind_synthetic_internal_token'
    || parsed.distinct_id !== 'flind-wave112-synthetic') {
    fail()
}
process.stdout.write(JSON.stringify({
    actual_typescript_deserializer_uuid_verified: true,
    source_record_was_real_native_capture_kafka: true,
    real_node_grpc_worker_qualified: false,
    real_rust_ingestion_consumer_qualified: false,
    release_qualified: false,
}) + '\n')
