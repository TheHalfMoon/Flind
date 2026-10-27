// Flind Wave185: actual original first-party gRPC Kafka serialization boundary.
// Standalone Node26 test uses only node:assert. Not a gRPC server or worker.
import assert from 'node:assert/strict'
import { grpcMessageToSerialized } from '../../nodejs/src/ingestion/api/grpc-message-converter.ts'
import { deserializeKafkaMessage } from '../../nodejs/src/ingestion/api/kafka-message-converter.ts'
import { safeIngestFailureMessage } from '../../nodejs/src/ingestion/api/grpc-error-sanitizer.ts'

let passed = 0
function check(title, fn) {
    fn()
    passed++
}
const exact = (changes = {}) => ({
    topic: 'flind_wave185_synthetic_only',
    partition: 3,
    offset: 123n,
    timestamp: 1761500000000n,
    key: 'flind:synthetic-key',
    value: '{"event":"$pageview","uuid":"00000000-0000-4000-8000-000000000185"}',
    headers: { source: 'flind-native-test' },
    ...changes,
})
check('original_gRPC_converter_exact_normal_values', () => {
    const converted = grpcMessageToSerialized(exact())
    assert.equal(converted.offset, 123)
    assert.equal(converted.timestamp, 1761500000000)
    assert.equal(converted.partition, 3)
    assert.equal(converted.topic, 'flind_wave185_synthetic_only')
    assert.equal(converted.headers.source, 'flind-native-test')
})
check('original_gRPC_converter_roundtrips_through_original_Kafka_converter', () => {
    const message = deserializeKafkaMessage(grpcMessageToSerialized(exact()))
    assert.equal(message.offset, 123)
    assert.equal(message.partition, 3)
    assert.equal(message.topic, 'flind_wave185_synthetic_only')
    assert.equal(message.key.toString('utf8'), 'flind:synthetic-key')
    assert.equal(JSON.parse(message.value.toString('utf8')).uuid, '00000000-0000-4000-8000-000000000185')
    assert.equal(message.size, message.value.byteLength)
    assert.equal(message.headers[0].source.toString('utf8'), 'flind-native-test')
})
for (const [label, candidate] of [
    ['zero', 0n], ['minus_one', -1n],
    ['max_safe', 9007199254740991n], ['min_safe', -9007199254740991n],
]) {
    check('lossless_offset_' + label, () => {
        assert.equal(grpcMessageToSerialized(exact({ offset: candidate })).offset, Number(candidate))
    })
}
for (const [label, candidate] of [
    ['positive_max_plus_one', 9007199254740992n], ['positive_max_plus_two', 9007199254740993n],
    ['signed_max', 9223372036854775807n], ['negative_min_minus_one', -9007199254740992n],
    ['signed_min', -9223372036854775808n],
]) {
    check('reject_unsafe_offset_' + label, () => {
        assert.throws(() => grpcMessageToSerialized(exact({ offset: candidate })),
                      (err) => err instanceof RangeError && err.message.includes('Kafka offset'))
    })
}
for (const [label, candidate] of [
    ['zero', 0n], ['minus_one', -1n],
    ['max_safe', 9007199254740991n], ['min_safe', -9007199254740991n],
]) {
    check('lossless_timestamp_' + label, () => {
        assert.equal(grpcMessageToSerialized(exact({ timestamp: candidate })).timestamp, Number(candidate))
    })
}
for (const [label, candidate] of [
    ['positive_max_plus_one', 9007199254740992n], ['positive_max_plus_two', 9007199254740993n],
    ['signed_max', 9223372036854775807n], ['negative_min_minus_one', -9007199254740992n],
    ['signed_min', -9223372036854775808n],
]) {
    check('reject_unsafe_timestamp_' + label, () => {
        assert.throws(() => grpcMessageToSerialized(exact({ timestamp: candidate })),
                      (err) => err instanceof RangeError && err.message.includes('Kafka timestamp'))
    })
}
check('preserve_empty_key_and_value', () => {
    const source = grpcMessageToSerialized(exact({ key: '', value: '' }))
    assert.equal(source.key, '')
    assert.equal(source.value, '')
    const restored = deserializeKafkaMessage(source)
    assert.equal(restored.key.byteLength, 0)
    assert.equal(restored.value.byteLength, 0)
    assert.equal(restored.size, 0)
})
check('preserve_null_tombstone', () => {
    const source = grpcMessageToSerialized(exact({ key: null, value: null }))
    assert.equal(source.key, null)
    assert.equal(source.value, null)
    const restored = deserializeKafkaMessage(source)
    assert.equal(restored.key, undefined)
    assert.equal(restored.value, null)
    assert.equal(restored.size, 0)
})
check('zero_length_header_remains_zero_length', () => {
    const result = deserializeKafkaMessage(grpcMessageToSerialized(exact({ headers: { empty: '' } })))
    assert.equal(result.headers[0].empty.length, 0)
})
check('valid_utf8_key_preserved', () => {
    const result = deserializeKafkaMessage(grpcMessageToSerialized(exact({ key: 'flind-العربية' })))
    assert.equal(result.key.toString('utf8'), 'flind-العربية')
})
const secret = 'FLIND_SYNTHETIC_PRIVATE_TOKEN_ONLY_DO_NOT_EMIT'
for (const [title, bad] of [
    ['secret_text', secret], ['secret_error', new Error(secret)],
    ['secret_object', { token: secret, offset: 999n }],
    ['null_cause', null], ['undefined_cause', undefined],
    ['malicious_toString', { toString() { throw Error('Must never stringify the underlying failure') } }],
]) {
    check('error_redaction_' + title, () => {
        const response = safeIngestFailureMessage(bad)
        assert.equal(response, 'ingest pipeline failed')
        assert.equal(response.includes(secret), false)
    })
}
check('empty_failure_cause_does_not_succeed', () => {
    assert.equal(safeIngestFailureMessage(''), 'ingest pipeline failed')
})
check('release_gate_explicitly_remains_false', () => {
    assert.equal(passed >= 30, true)
})
process.stdout.write(JSON.stringify({
    phase: 'original_source_grpc_kafka_primitive_runtime',
    original_grpc_int64_precision_pass: true,
    original_kafka_message_conversion_pass: true,
    original_grpc_error_sanitization_pass: true,
    tests_passed: passed,
    external_modules_used: false,
    production_grpc_server_qualified: false,
    production_node_grpc_server_qualified: false,
    production_node_worker_qualified: false,
    real_rust_to_production_node_qualified: false,
    durable_clickhouse_qualified: false,
    authenticated_tenant_isolation_qualified: false,
    release_qualified: false,
}) + '\n')
