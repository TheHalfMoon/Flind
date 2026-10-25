import { drainAndDisconnectConsumer } from './consumer-loop-cleanup'

const deferred = () => {
    let resolve!: () => void
    let reject!: (error: Error) => void
    const promise = new Promise<void>((good, bad) => {
        resolve = good
        reject = bad
    })
    return { promise, resolve, reject }
}

describe('Kafka v1 consumer loop cleanup (Wave 93)', () => {
    it('waits for all tasks after first failure before disconnecting', async () => {
        const first = deferred()
        const second = deferred()
        const problem = new Error('synthetic batch failure')
        const disconnect = jest.fn().mockResolvedValue(undefined)
        const shutdown = drainAndDisconnectConsumer(
            [first.promise, second.promise],
            { failed: true, drain: async () => undefined },
            disconnect
        )
        first.reject(problem)
        await Promise.resolve()
        expect(disconnect).not.toHaveBeenCalled()
        second.resolve()
        await expect(shutdown).rejects.toBe(problem)
        expect(disconnect).toHaveBeenCalledTimes(1)
    })

    it('retains both failed background processing and failed Kafka disconnect', async () => {
        const taskError = new Error('synthetic processing failure')
        const disconnectError = new Error('synthetic disconnection failure')
        let cause: unknown
        try {
            await drainAndDisconnectConsumer(
                [Promise.reject(taskError)],
                { failed: true, drain: async () => undefined },
                async () => { throw disconnectError },
                taskError
            )
        } catch (error) {
            cause = error
        }
        expect(cause).toBeInstanceOf(AggregateError)
        expect((cause as AggregateError).errors).toEqual([taskError, disconnectError])
    })

    it('still closes native Kafka when the ordered offset gate drain throws', async () => {
        const gateError = new Error('synthetic offset drain error')
        const disconnect = jest.fn().mockResolvedValue(undefined)
        await expect(
            drainAndDisconnectConsumer([], { failed: false, drain: async () => { throw gateError } }, disconnect)
        ).rejects.toBe(gateError)
        expect(disconnect).toHaveBeenCalledTimes(1)
    })

    it('completes cleanly when no task or gate failure exists', async () => {
        const disconnect = jest.fn().mockResolvedValue(undefined)
        await expect(drainAndDisconnectConsumer([Promise.resolve()], {
            failed: false,
            drain: async () => undefined,
        }, disconnect)).resolves.toBeUndefined()
        expect(disconnect).toHaveBeenCalledTimes(1)
    })

    it('reports poisoned offsets even when finished background work was already removed', async () => {
        const disconnect = jest.fn().mockResolvedValue(undefined)
        await expect(drainAndDisconnectConsumer([], {
            failed: true,
            drain: async () => undefined,
        }, disconnect)).rejects.toThrow('offset store failed')
        expect(disconnect).toHaveBeenCalledTimes(1)
    })

    it('preserves distinct loop, batch and disconnect failures in deterministic order', async () => {
        const loop = new Error('loop failed')
        const task = new Error('batch failed')
        const disconnect = new Error('close failed')
        let cause: unknown
        try {
            await drainAndDisconnectConsumer(
                [Promise.reject(task)],
                { failed: true, drain: async () => undefined },
                async () => { throw disconnect },
                loop
            )
        } catch (error) {
            cause = error
        }
        expect(cause).toBeInstanceOf(AggregateError)
        expect((cause as AggregateError).errors).toEqual([loop, task, disconnect])
    })

    it('deduplicates one task failure already reported by the loop', async () => {
        const error = new Error('same background failure')
        await expect(drainAndDisconnectConsumer(
            [Promise.reject(error)],
            { failed: true, drain: async () => undefined },
            async () => undefined,
            error
        )).rejects.toBe(error)
    })

    it('never attempts disconnect before pending work and ordered offsets finish', async () => {
        const task = deferred()
        const gate = deferred()
        const disconnect = jest.fn().mockResolvedValue(undefined)
        const shutdown = drainAndDisconnectConsumer([task.promise], { failed: false, drain: () => gate.promise }, disconnect)
        await Promise.resolve()
        expect(disconnect).not.toHaveBeenCalled()
        task.resolve()
        await Promise.resolve()
        expect(disconnect).not.toHaveBeenCalled()
        gate.resolve()
        await shutdown
        expect(disconnect).toHaveBeenCalledTimes(1)
    })
})
