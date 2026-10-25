import { Message } from 'node-rdkafka'

import { KafkaConsumerInterface, createKafkaConsumer } from '~/common/kafka/consumer'
import { instrumentFn } from '~/common/tracing/tracing-utils'
import { Component } from '~/ingestion/common/scopes'

export { createKafkaConsumer } from '~/common/kafka/consumer'
export type { KafkaConsumerInterface } from '~/common/kafka/consumer'

/**
 * Owns a Kafka consumer's lifetime as a scope entry. Start creates the
 * consumer and connects it to the provided per-batch handler; stop
 * disconnects it. Failures during connect cause the surrounding scope
 * to roll back already-started entries.
 */
export class KafkaConsumerComponent implements Component<KafkaConsumerInterface> {
    constructor(
        private readonly groupId: string,
        private readonly topic: string,
        private readonly handler: (messages: Message[]) => Promise<{ backgroundTask?: Promise<unknown> }>
    ) {}

    async start(): Promise<{ value: KafkaConsumerInterface; stop: () => Promise<void> }> {
        const kafkaConsumer = createKafkaConsumer({ groupId: this.groupId, topic: this.topic })
        try {
            await kafkaConsumer.connect(
                async (messages: Message[]) =>
                    await instrumentFn(
                        { key: 'commonIngestionConsumer.handleEachBatch', sendException: false },
                        async () => await this.handler(messages)
                    )
            )
        } catch (connectError) {
            // start() has not returned a stop handle yet, so the owning
            // ScopeRunner cannot clean up this partially started consumer.
            // Disconnect here, preserving both failures if cleanup fails.
            try {
                await kafkaConsumer.disconnect()
            } catch (disconnectError) {
                throw new AggregateError(
                    [connectError, disconnectError],
                    'Kafka consumer connection failed and cleanup also failed'
                )
            }
            throw connectError
        }
        return {
            value: kafkaConsumer,
            stop: () => kafkaConsumer.disconnect(),
        }
    }
}
