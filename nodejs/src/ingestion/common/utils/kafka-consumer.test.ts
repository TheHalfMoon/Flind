import { createKafkaConsumer, KafkaConsumerInterface } from '~/common/kafka/consumer'
import { instrumentFn } from '~/common/tracing/tracing-utils'

import { KafkaConsumerComponent } from './kafka-consumer'

jest.mock('~/common/kafka/consumer', () => ({
    createKafkaConsumer: jest.fn(),
}))
jest.mock('~/common/tracing/tracing-utils', () => ({
    instrumentFn: jest.fn(async (_options, callback) => await callback()),
}))

describe('KafkaConsumerComponent startup lifecycle', () => {
    const consumer = {
        connect: jest.fn(),
        disconnect: jest.fn(),
    }

    beforeEach(() => {
        jest.clearAllMocks()
        consumer.connect.mockReset().mockResolvedValue(undefined)
        consumer.disconnect.mockReset().mockResolvedValue(undefined)
        jest.mocked(createKafkaConsumer).mockReturnValue(consumer as unknown as KafkaConsumerInterface)
    })

    function component(handler = jest.fn().mockResolvedValue({})) {
        return { instance: new KafkaConsumerComponent('events-group', 'events-topic', handler), handler }
    }

    it('connects once and defers disconnect until the successful scope stop', async () => {
        const { instance } = component()
        const started = await instance.start()

        expect(createKafkaConsumer).toHaveBeenCalledWith({ groupId: 'events-group', topic: 'events-topic' })
        expect(consumer.connect).toHaveBeenCalledTimes(1)
        expect(consumer.disconnect).not.toHaveBeenCalled()
        expect(started.value).toBe(consumer)

        await started.stop()
        expect(consumer.disconnect).toHaveBeenCalledTimes(1)
    })

    it('keeps the instrumented batch handler after successful connection', async () => {
        const { instance, handler } = component()
        const started = await instance.start()
        const callback = consumer.connect.mock.calls[0][0] as Parameters<KafkaConsumerInterface['connect']>[0]
        const messages = [] as Parameters<Parameters<KafkaConsumerInterface['connect']>[0]>[0]

        await callback(messages)
        expect(handler).toHaveBeenCalledWith(messages)
        expect(instrumentFn).toHaveBeenCalledWith(
            { key: 'commonIngestionConsumer.handleEachBatch', sendException: false },
            expect.any(Function)
        )
        await started.stop()
    })

    it('disconnects a partially created consumer when connect rejects and preserves the original error', async () => {
        const failure = new Error('synthetic broker connection refused')
        consumer.connect.mockRejectedValue(failure)
        const { instance } = component()

        await expect(instance.start()).rejects.toBe(failure)
        expect(consumer.disconnect).toHaveBeenCalledTimes(1)
    })

    it('also cleans up when connect throws synchronously', async () => {
        const failure = new Error('synthetic configuration failed')
        consumer.connect.mockImplementation(() => {
            throw failure
        })

        await expect(component().instance.start()).rejects.toBe(failure)
        expect(consumer.disconnect).toHaveBeenCalledTimes(1)
    })

    it('preserves both failure causes if connect and disconnect both fail', async () => {
        const connectFailure = new Error('synthetic broker timeout')
        const cleanupFailure = new Error('synthetic disconnect timeout')
        consumer.connect.mockRejectedValue(connectFailure)
        consumer.disconnect.mockRejectedValue(cleanupFailure)

        let caught: unknown
        try {
            await component().instance.start()
        } catch (error) {
            caught = error
        }
        expect(caught).toBeInstanceOf(AggregateError)
        expect((caught as AggregateError).errors).toEqual([connectFailure, cleanupFailure])
        expect(consumer.disconnect).toHaveBeenCalledTimes(1)
    })

    it('does not call disconnect twice when connect fails', async () => {
        consumer.connect.mockRejectedValue(new Error('synthetic broker unavailable'))
        await expect(component().instance.start()).rejects.toThrow('synthetic broker unavailable')
        expect(consumer.disconnect).toHaveBeenCalledTimes(1)
    })
})
