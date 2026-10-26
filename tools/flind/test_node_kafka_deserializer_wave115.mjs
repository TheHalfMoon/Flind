// Wave115: run the ACTUAL TypeScript production Rust→Node Kafka converter
// directly with native Node's TypeScript type stripping; no pnpm/Jest install.
import test from 'node:test'
import assert from 'node:assert/strict'
import { deserializeKafkaMessage } from '../../nodejs/src/ingestion/api/kafka-message-converter.ts'

const fixture = (key, value, headers = {}) => ({
    topic: 'flind-wave115-test',
    partition: 2,
    offset: 123,
    timestamp: 1700000000000,
    key,
    value,
    headers,
})

test('zero-byte Kafka key and value are Buffers, not tombstones', () => {
    const message = deserializeKafkaMessage(fixture('', '', { empty: '' }))
    assert.deepStrictEqual(message.key, Buffer.alloc(0))
    assert.deepStrictEqual(message.value, Buffer.alloc(0))
    assert.equal(message.size, 0)
    assert.deepStrictEqual(message.headers, [{ empty: Buffer.alloc(0) }])
    assert.equal(message.topic, 'flind-wave115-test')
    assert.equal(message.partition, 2)
    assert.equal(message.offset, 123)
    assert.equal(message.timestamp, 1700000000000)
})

test('null Kafka key/value remains absent/tombstone', () => {
    const message = deserializeKafkaMessage(fixture(null, null))
    assert.equal(message.key, undefined)
    assert.equal(message.value, null)
    assert.equal(message.size, 0)
    assert.equal(message.headers, undefined)
})

test('zero-byte key with real tombstone preserves null payload', () => {
    const message = deserializeKafkaMessage(fixture('', null))
    assert.deepStrictEqual(message.key, Buffer.alloc(0))
    assert.equal(message.value, null)
})

test('zero-byte payload with null key preserves Buffer', () => {
    const message = deserializeKafkaMessage(fixture(null, ''))
    assert.equal(message.key, undefined)
    assert.deepStrictEqual(message.value, Buffer.alloc(0))
    assert.equal(message.size, 0)
})

test('ordinary JSON Kafka message preserves key, payload and headers', () => {
    const input = '{"event":"$pageview","properties":{"$pathname":"/home"}}'
    const message = deserializeKafkaMessage(fixture('team:person', input, { token: 'synthetic' }))
    assert.deepStrictEqual(message.key, Buffer.from('team:person'))
    assert.deepStrictEqual(message.value, Buffer.from(input))
    assert.equal(message.size, Buffer.byteLength(input))
    assert.deepStrictEqual(message.headers, [{ token: Buffer.from('synthetic') }])
})

test('Unicode content measures UTF-8 bytes, not JavaScript code units', () => {
    const input = '{"text":"José 日本語 🎉"}'
    const message = deserializeKafkaMessage(fixture('synthetic', input))
    assert.equal(message.value.toString('utf8'), input)
    assert.equal(message.size, Buffer.byteLength(input, 'utf8'))
    assert.ok(message.size > input.length)
})

test('empty payload is not equal to null tombstone, even when both size zero', () => {
    const empty = deserializeKafkaMessage(fixture('s', ''))
    const tombstone = deserializeKafkaMessage(fixture('s', null))
    assert.equal(empty.size, tombstone.size)
    assert.ok(Buffer.isBuffer(empty.value))
    assert.equal(tombstone.value, null)
})
