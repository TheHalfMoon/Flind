export class PromiseScheduler {
    public readonly promises: Set<Promise<any>> = new Set()
    // A failed side effect can settle before waitForAll() snapshots the Set.
    // Retain the first rejection until this scheduler is recreated: an ACK
    // barrier must never forget an already-failed durable side effect.
    private firstFailure: { reason: unknown } | null = null

    public schedule<T>(promise: Promise<T>): Promise<T>
    public schedule<T extends readonly [Promise<unknown>, Promise<unknown>, ...Promise<unknown>[]]>(
        ...promises: T
    ): Promise<{ -readonly [K in keyof T]: Awaited<T[K]> }>
    public schedule(...promises: Promise<unknown>[]): Promise<unknown> {
        for (const promise of promises) {
            this.promises.add(promise)
            const cleanup = () => this.promises.delete(promise)
            promise.then(cleanup, (reason) => {
                this.firstFailure ??= { reason }
                cleanup()
            })
        }
        return promises.length === 1 ? promises[0] : Promise.all(promises)
    }

    public async waitForAll() {
        if (this.firstFailure) {
            throw this.firstFailure.reason
        }
        const results = await Promise.all(this.promises)
        // A promise may reject while the snapshot is settling, or it may
        // already have left the Set before this barrier was entered.
        if (this.firstFailure) {
            throw this.firstFailure.reason
        }
        return results
    }

    public async waitForAllSettled() {
        return await Promise.allSettled(this.promises)
    }
}
