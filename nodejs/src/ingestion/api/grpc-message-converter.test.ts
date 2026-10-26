import { grpcMessageToSerialized } from './grpc-message-converter'

const message = (changes: Record<string, unknown> = {}) =>
    ({
        topic: 'events_plugin_ingestion',
        partition: 3,
        offset: 123n,
        timestamp: 1761500000000n,
        key: 'token:synthetic',
        value: '{"event":"$pageview"}',
        headers: { source: 'rust-consumer' },
        ...changes,
    }) as Parameters<typeof grpcMessageToSerialized>[0]

describe('grpcMessageToSerialized protobuf int64 admission', () => {
    it('preserves normal values, metadata, and exact Kafka position', () => {
        const input = message()
        expect(grpcMessageToSerialized(input)).toEqual({
            topic: 'events_plugin_ingestion',
            partition: 3,
            offset: 123,
            timestamp: 1761500000000,
            key: 'token:synthetic',
            value: '{"event":"$pageview"}',
            headers: { source: 'rust-consumer' },
        })
    })

    it('preserves empty Kafka key/value versus null tombstones', () => {
        expect(grpcMessageToSerialized(message({ key: '', value: '' }))).toMatchObject({
            key: '',
            value: '',
        })
        expect(grpcMessageToSerialized(message({ key: null, value: null }))).toMatchObject({
            key: null,
            value: null,
        })
    })

    it.each([BigInt(Number.MAX_SAFE_INTEGER), BigInt(Number.MIN_SAFE_INTEGER), -1n, 0n])(
        'accepts exactly representable Kafka offset %s',
        (offset) => {
            expect(grpcMessageToSerialized(message({ offset })).offset).toBe(Number(offset))
        }
    )

    it.each([9007199254740992n, 9007199254740993n, 9223372036854775807n])(
        'refuses a rounded Kafka offset %s instead of acknowledging the wrong event',
        (offset) => {
            expect(() => grpcMessageToSerialized(message({ offset }))).toThrow(RangeError)
            expect(() => grpcMessageToSerialized(message({ offset }))).toThrow(/Kafka offset/)
        }
    )

    it.each([9007199254740992n, -9007199254740992n, 9223372036854775807n])(
        'refuses an unsafe Protobuf timestamp %s',
        (timestamp) => {
            expect(() => grpcMessageToSerialized(message({ timestamp }))).toThrow(RangeError)
            expect(() => grpcMessageToSerialized(message({ timestamp }))).toThrow(/Kafka timestamp/)
        }
    )
})
