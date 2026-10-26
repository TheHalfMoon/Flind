import type { Message, MessageHeader } from 'node-rdkafka'

import type { SerializedKafkaMessage } from './types'

/**
 * Converts a SerializedKafkaMessage (from the Rust consumer HTTP API)
 * back into a node-rdkafka Message for the ingestion pipeline.
 */
export function deserializeKafkaMessage(serialized: SerializedKafkaMessage): Message {
    const headers: MessageHeader[] = Object.entries(serialized.headers).map(([key, value]) => ({
        [key]: Buffer.from(value, 'utf-8'),
    }))

    // Kafka distinguishes a zero-byte value from a null tombstone. Do not
    // interpret an empty string as deletion during Rust → Node conversion.
    const valueBuffer = serialized.value === null ? null : Buffer.from(serialized.value, 'utf-8')

    return {
        topic: serialized.topic,
        partition: serialized.partition,
        offset: serialized.offset,
        timestamp: serialized.timestamp,
        size: valueBuffer?.byteLength ?? 0,
        key: serialized.key === null ? undefined : Buffer.from(serialized.key, 'utf-8'),
        value: valueBuffer,
        headers: headers.length > 0 ? headers : undefined,
    }
}
