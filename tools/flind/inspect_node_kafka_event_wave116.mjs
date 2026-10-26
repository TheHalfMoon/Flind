// Wave116 — consume a real Rust-produced Kafka event through Flind's
// ACTUAL production TypeScript ingestion deserializer, using only native Node.
// stdin is bounded, synthetic JSON from the independent Kafka consumer.
// The wrapper around the Kafka record is a TEST FIXTURE, NOT the real gRPC
// Rust-consumer API. This DOES NOT execute the production ingestion worker.
import { deserializeKafkaMessage } from '../../nodejs/src/ingestion/api/kafka-message-converter.ts'

const MAX_BYTES = 64 * 1024
let text = ''
for await (const part of process.stdin) {
    text += part.toString('utf8')
    if (Buffer.byteLength(text) > MAX_BYTES) {
        process.stderr.write('synthetic Kafka fixture too large\n')
        process.exit(2)
    }
}

const fail = (reason) => {
    process.stderr.write(reason + '\n')
    process.exit(2)
}

let input
try {
    input = JSON.parse(text)
} catch {
    fail('invalid fixture envelope')
}
if (!input || typeof input !== 'object' || !input.event || typeof input.event !== 'object') {
    fail('event fixture missing')
}
const record = input.event
if (
    input.topic !== 'flind-wave113-native-analytics'
    || !/^[a-f0-9-]{36}$/i.test(record.uuid ?? '')
    || record.event !== '$pageview'
    || record.distinct_id !== 'flind-wave112-synthetic'
    || record.token !== 'flind_synthetic_internal_token'
) {
    fail('not the expected native synthetic Capture event')
}

const value = JSON.stringify(record)
const serialized = {
    topic: input.topic,
    partition: 0,
    offset: 0,
    timestamp: 0,
    key: null,
    value,
    headers: {},
}
const message = deserializeKafkaMessage(serialized)
const parsed = JSON.parse(message.value.toString('utf8'))
const pass =
    message.topic === input.topic
    && Buffer.isBuffer(message.value)
    && message.size === Buffer.byteLength(value, 'utf8')
    && message.key === undefined
    && parsed.uuid === record.uuid
    && parsed.event === '$pageview'
    && parsed.distinct_id === 'flind-wave112-synthetic'
    && parsed.token === 'flind_synthetic_internal_token'
if (!pass) {
    fail('real production deserializer misread synthetic Kafka record')
}
process.stdout.write(JSON.stringify({
    source_record_was_native_rust_kafka: true,
    production_typescript_deserializer_executed: true,
    uuid_preserved_in_node_buffer: true,
    token_and_distinct_id_preserved: true,
    actual_node_ingestion_worker_qualified: false,
    actual_rust_ingestion_consumer_api_qualified: false,
    production_clickhouse_schema_qualified: false,
    release_qualified: false,
}) + '\n')
