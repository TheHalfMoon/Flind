import { deserializeKafkaMessage } from './kafka-message-converter'
import { SerializedKafkaMessage } from './types'

describe('deserializeKafkaMessage', () => {
    it('converts a full message with all fields', () => {
        const serialized: SerializedKafkaMessage = {
            topic: 'events_plugin_ingestion',
            partition: 3,
            offset: 42,
            timestamp: 1700000000000,
            key: 'my-token:my-distinct-id',
            value: '{"event":"$pageview","properties":{"$current_url":"https://example.com"}}',
            headers: {
                token: 'my-token',
                distinct_id: 'my-distinct-id',
            },
        }

        const message = deserializeKafkaMessage(serialized)

        expect(message.topic).toBe('events_plugin_ingestion')
        expect(message.partition).toBe(3)
        expect(message.offset).toBe(42)
        expect(message.timestamp).toBe(1700000000000)
        expect(message.key).toEqual(Buffer.from('my-token:my-distinct-id'))
        expect(message.value).toEqual(
            Buffer.from('{"event":"$pageview","properties":{"$current_url":"https://example.com"}}')
        )
        expect(message.headers).toEqual([
            { token: Buffer.from('my-token') },
            { distinct_id: Buffer.from('my-distinct-id') },
        ])
        expect(message.size).toBe(Buffer.byteLength(serialized.value!, 'utf-8'))
    })

    it('handles null key and value', () => {
        const serialized: SerializedKafkaMessage = {
            topic: 'test-topic',
            partition: 0,
            offset: 0,
            timestamp: 0,
            key: null,
            value: null,
            headers: {},
        }

        const message = deserializeKafkaMessage(serialized)

        expect(message.key).toBeUndefined()
        expect(message.value).toBeNull()
        expect(message.size).toBe(0)
        expect(message.headers).toBeUndefined()
    })

    it('keeps zero-byte key and value distinct from Kafka null tombstones', () => {
        const serialized: SerializedKafkaMessage = {
            topic: 'test-topic', partition: 1, offset: 4, timestamp: 0,
            key: '', value: '', headers: { empty: '' },
        }

        const message = deserializeKafkaMessage(serialized)
        expect(message.key).toEqual(Buffer.alloc(0))
        expect(message.value).toEqual(Buffer.alloc(0))
        expect(message.size).toBe(0)
        expect(message.headers).toEqual([{ empty: Buffer.alloc(0) }])
    })

    it('preserves a null Kafka tombstone with a valid empty key', () => {
        const serialized: SerializedKafkaMessage = {
            topic: 'test-topic', partition: 0, offset: 5, timestamp: 0,
            key: '', value: null, headers: {},
        }
        const message = deserializeKafkaMessage(serialized)
        expect(message.key).toEqual(Buffer.alloc(0))
        expect(message.value).toBeNull()
        expect(message.size).toBe(0)
    })

    it('preserves an empty payload with a null key', () => {
        const serialized: SerializedKafkaMessage = {
            topic: 'test-topic', partition: 0, offset: 6, timestamp: 0,
            key: null, value: '', headers: {},
        }
        const message = deserializeKafkaMessage(serialized)
        expect(message.key).toBeUndefined()
        expect(message.value).toEqual(Buffer.alloc(0))
        expect(message.size).toBe(0)
    })

    it('handles empty headers', () => {
        const serialized: SerializedKafkaMessage = {
            topic: 'test-topic',
            partition: 0,
            offset: 0,
            timestamp: 0,
            key: 'key',
            value: '{}',
            headers: {},
        }

        const message = deserializeKafkaMessage(serialized)

        expect(message.headers).toBeUndefined()
    })

    it('handles unicode content in value', () => {
        const serialized: SerializedKafkaMessage = {
            topic: 'test-topic',
            partition: 0,
            offset: 0,
            timestamp: 0,
            key: null,
            value: '{"name":"José 日本語 🎉"}',
            headers: {},
        }

        const message = deserializeKafkaMessage(serialized)

        expect(message.value!.toString('utf-8')).toBe('{"name":"José 日本語 🎉"}')
        // size should reflect byte length, not JS string length (multi-byte chars)
        expect(message.size).toBe(Buffer.byteLength('{"name":"José 日本語 🎉"}', 'utf-8'))
    })
})
