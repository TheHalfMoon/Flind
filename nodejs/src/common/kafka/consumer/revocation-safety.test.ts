import { awaitRevocationSafety } from './revocation-safety'

const deferred = (): {
    promise: Promise<void>
    resolve: () => void
    reject: (error: Error) => void
} => {
    let resolve!: () => void
    let reject!: (error: Error) => void
    const promise = new Promise<void>((good, bad) => {
        resolve = good
        reject = bad
    })
    return { promise, resolve, reject }
}

describe('Kafka v1 background revocation safety', () => {
    it('does not relinquish a partition early when an earlier batch fails', async () => {
        const first = deferred()
        const second = deferred()
        const drain = jest.fn().mockResolvedValue(undefined)
        let finished = false
        const report = awaitRevocationSafety([first.promise, second.promise], { failed: true, drain }).then((value) => {
            finished = true
            return value
        })

        first.reject(new Error('synthetic first batch failure'))
        await Promise.resolve()
        expect(finished).toBe(false)
        expect(drain).not.toHaveBeenCalled()
        second.resolve()
        await expect(report).resolves.toEqual({ failedTasks: 1, offsetGateFailed: true })
        expect(drain).toHaveBeenCalledTimes(1)
    })

    it('waits for earlier work after a later batch fails', async () => {
        const first = deferred()
        const second = deferred()
        const drain = jest.fn().mockResolvedValue(undefined)
        const report = awaitRevocationSafety([first.promise, second.promise], { failed: true, drain })
        second.reject(new Error('synthetic later batch failure'))
        await Promise.resolve()
        expect(drain).not.toHaveBeenCalled()
        first.resolve()
        await expect(report).resolves.toEqual({ failedTasks: 1, offsetGateFailed: true })
    })

    it('drains pending offset stores even with an empty background task snapshot', async () => {
        const release = deferred()
        const drain = jest.fn(() => release.promise)
        let finished = false
        const result = awaitRevocationSafety([], { failed: false, drain }).then((value) => {
            finished = true
            return value
        })
        await Promise.resolve()
        expect(drain).toHaveBeenCalledTimes(1)
        expect(finished).toBe(false)
        release.resolve()
        await expect(result).resolves.toEqual({ failedTasks: 0, offsetGateFailed: false })
    })

    it('propagates a failed offset gate drain instead of claiming safe completion', async () => {
        const error = new Error('synthetic offset store drain failed')
        await expect(awaitRevocationSafety([], { failed: true, drain: async () => { throw error } })).rejects.toBe(error)
    })

    it('returns a healthy receipt only when all tasks and stores succeed', async () => {
        expect(
            await awaitRevocationSafety([Promise.resolve(), Promise.resolve()], {
                failed: false,
                drain: async () => undefined,
            })
        ).toEqual({ failedTasks: 0, offsetGateFailed: false })
    })

    it('reports all rejected tasks rather than short-circuiting on the first', async () => {
        expect(
            await awaitRevocationSafety(
                [Promise.reject(new Error('first')), Promise.reject(new Error('second')), Promise.resolve()],
                { failed: true, drain: async () => undefined }
            )
        ).toEqual({ failedTasks: 2, offsetGateFailed: true })
    })
})
