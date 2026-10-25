import { OffsetCommitGate } from './offset-commit-gate'

function deferred(): { promise: Promise<void>; resolve: () => void; reject: (error: Error) => void } {
    let resolve!: () => void
    let reject!: (error: Error) => void
    const promise = new Promise<void>((good, bad) => {
        resolve = good
        reject = bad
    })
    return { promise, resolve, reject }
}

describe('OffsetCommitGate — Kafka v1 safety', () => {
    it('stores successful batches in Kafka arrival order even when work finishes out of order', async () => {
        const gate = new OffsetCommitGate()
        const a = deferred()
        const b = deferred()
        const stored: number[] = []

        gate.observe(a.promise, () => stored.push(101))
        gate.observe(b.promise, () => stored.push(202))
        b.resolve()
        await Promise.resolve()
        expect(stored).toEqual([])
        a.resolve()
        await gate.drain()
        expect(stored).toEqual([101, 202])
        expect(gate.failed).toBe(false)
    })

    it('does not acknowledge a successful later batch over a failed earlier batch', async () => {
        const gate = new OffsetCommitGate()
        const a = deferred()
        const b = deferred()
        const stored: number[] = []

        gate.observe(a.promise, () => stored.push(101))
        gate.observe(b.promise, () => stored.push(202))
        b.resolve()
        a.reject(new Error('synthetic failed first batch'))
        await gate.drain()
        expect(stored).toEqual([])
        expect(gate.failed).toBe(true)
    })

    it('fences earlier pending work when a later batch has already failed', async () => {
        const gate = new OffsetCommitGate()
        const a = deferred()
        const b = deferred()
        const stored: number[] = []

        gate.observe(a.promise, () => stored.push(101))
        gate.observe(b.promise, () => stored.push(202))
        b.reject(new Error('synthetic failed later batch'))
        await Promise.resolve()
        a.resolve()
        await gate.drain()
        expect(stored).toEqual([])
        expect(gate.failed).toBe(true)
    })

    it('permanently refuses future acknowledgements after a rejected background task', async () => {
        const gate = new OffsetCommitGate()
        const stored: number[] = []
        gate.observe(Promise.reject(new Error('synthetic failure')), () => stored.push(1))
        await gate.drain()
        gate.observe(Promise.resolve(), () => stored.push(2))
        await gate.drain()
        expect(stored).toEqual([])
        expect(gate.failed).toBe(true)
    })

    it('treats a thrown offsetsStore callback as fatal without creating unhandled rejections', async () => {
        const gate = new OffsetCommitGate()
        const stored: number[] = []
        gate.observe(Promise.resolve(), () => {
            throw new Error('synthetic offsetsStore failure')
        })
        await gate.drain()
        gate.observe(Promise.resolve(), () => stored.push(2))
        await gate.drain()
        expect(gate.failed).toBe(true)
        expect(stored).toEqual([])
    })

    it('acknowledges immediately successful work exactly once', async () => {
        const gate = new OffsetCommitGate()
        const stored: number[] = []
        gate.observe(Promise.resolve(), () => stored.push(9))
        await gate.drain()
        await gate.drain()
        expect(stored).toEqual([9])
    })
})
