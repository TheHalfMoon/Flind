import test from 'node:test'
import assert from 'node:assert/strict'

// The real first-party production TypeScript converter, with only type-only
// imports so Node 26 runs it without a full npm/pnpm workspace install.
import { grpcMessageToSerialized } from '../../nodejs/src/ingestion/api/grpc-message-converter.ts'

const message = (overrides = {}) => ({
    topic: 'events_plugin_ingestion', partition: 3,
    offset: 1234567890123n, timestamp: 1761500000000n,
    key: 'flind:test-user', value: '{"event":"$pageview"}',
    headers: { source: 'native-rust', empty: '' },
    ...overrides,
})

test('ordinary first-party Kafka gRPC record retains exact offset/timestamp and data', () => {
    const value = message()
    const wire = grpcMessageToSerialized(value)
    assert.equal(wire.topic, value.topic)
    assert.equal(wire.partition, value.partition)
    assert.equal(wire.offset, 1234567890123)
    assert.equal(wire.timestamp, 1761500000000)
    assert.equal(wire.key, value.key)
    assert.equal(wire.value, value.value)
    assert.deepEqual(wire.headers, value.headers)
})

test('Kafka zero-byte key and value remain non-null empty strings', () => {
    const result = grpcMessageToSerialized(message({ key: '', value: '', headers: {} }))
    assert.equal(result.key, '')
    assert.equal(result.value, '')
    assert.deepEqual(result.headers, {})
})

test('Kafka null tombstone value and key remain null', () => {
    const result = grpcMessageToSerialized(message({ key: null, value: null }))
    assert.equal(result.key, null)
    assert.equal(result.value, null)
})

test('safe integer edge boundary offsets are accepted exactly', () => {
    for (const edge of [0n, 1n, -1n, BigInt(Number.MAX_SAFE_INTEGER), BigInt(Number.MIN_SAFE_INTEGER)]) {
        assert.equal(grpcMessageToSerialized(message({offset: edge})).offset, Number(edge))
    }
})

test('unsafe positive offset immediately fails closed', () => {
    for (const offset of [9007199254740992n, 9007199254740993n, 9223372036854775807n]) {
        assert.throws(() => grpcMessageToSerialized(message({offset})), {
            name: 'RangeError',
            message: /Kafka offset is outside the safe JavaScript integer range/,
        })
    }
})

test('unsafe negative offset fails closed', () => {
    for (const offset of [-9007199254740992n, -9007199254740993n, -9223372036854775808n]) {
        assert.throws(() => grpcMessageToSerialized(message({offset})), RangeError)
    }
})

test('unsafe timestamp fails closed without imprecise rounding', () => {
    for (const timestamp of [9007199254740992n, 9007199254740993n, 9223372036854775807n]) {
        assert.throws(() => grpcMessageToSerialized(message({timestamp})), {
            name: 'RangeError',
            message: /Kafka timestamp is outside the safe JavaScript integer range/,
        })
    }
})

test('safe negative timestamp and zero are preserved exactly', () => {
    assert.equal(grpcMessageToSerialized(message({timestamp: 0n})).timestamp, 0)
    assert.equal(grpcMessageToSerialized(message({timestamp: -1n})).timestamp, -1)
})

test('no mutation of input headers or Kafka metadata', () => {
    const original = message({headers: Object.freeze({topic: 'synthetic'})})
    Object.freeze(original)
    const converted = grpcMessageToSerialized(original)
    assert.equal(converted.headers.topic, 'synthetic')
    assert.equal(original.offset, 1234567890123n)
})

test('valid Unicode event data remains unmodified', () => {
    const payload = '{"event":"$pageview","text":"مرحبا 🎉"}'
    assert.equal(grpcMessageToSerialized(message({value: payload})).value, payload)
})
