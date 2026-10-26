import type { KafkaMessage } from '~/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb'

import type { SerializedKafkaMessage } from './types'

/** A protobuf int64 converted to a JavaScript number must not silently round. */
function checkedInt64(value: bigint, field: 'offset' | 'timestamp'): number {
    const asNumber = Number(value)
    if (!Number.isSafeInteger(asNumber) || BigInt(asNumber) !== value) {
        throw new RangeError(`Kafka ${field} is outside the safe JavaScript integer range`)
    }
    return asNumber
}

/**
 * Convert a WorkerIngest gRPC message to the production Node ingestion shape.
 * Fail closed on offsets/timestamps that cannot be represented losslessly:
 * rounding Kafka offsets may acknowledge a different record or corrupt order.
 */
export function grpcMessageToSerialized(message: KafkaMessage): SerializedKafkaMessage {
    return {
        topic: message.topic,
        partition: message.partition,
        offset: checkedInt64(message.offset, 'offset'),
        timestamp: checkedInt64(message.timestamp, 'timestamp'),
        key: message.key ?? null,
        value: message.value ?? null,
        headers: message.headers,
    }
}
