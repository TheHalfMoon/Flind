/**
 * Orders acknowledgements by consumed batch, not background task completion.
 * A failed task permanently fences this consumer from storing newer offsets;
 * otherwise later successful batches could acknowledge earlier failed work.
 * This safety boundary deliberately does not depend on a Kafka connection.
 */
export class OffsetCommitGate {
    private tail: Promise<void> = Promise.resolve()
    private poisoned = false

    get failed(): boolean {
        return this.poisoned
    }

    observe(task: Promise<unknown>, store: () => void): void {
        // Observe both outcomes immediately: a later failure must block even
        // an older task whose background work settles afterwards.
        const completed = task.then(
            () => true,
            () => {
                this.poisoned = true
                return false
            }
        )
        const following = this.tail.then(async () => {
            const succeeded = await completed
            if (!this.poisoned && succeeded) {
                store()
            }
        })
        // An offsetsStore exception also fences future acknowledgements;
        // consume rejections so observers never create an unhandled promise.
        this.tail = following.catch(() => {
            this.poisoned = true
        })
    }

    async drain(): Promise<void> {
        await this.tail
    }
}
