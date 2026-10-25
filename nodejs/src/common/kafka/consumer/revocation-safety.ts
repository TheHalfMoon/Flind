import type { OffsetCommitGate } from './offset-commit-gate'

/**
 * Snapshot outstanding event work before giving Kafka partitions away.
 * Promise.all would reject at the first failure and prematurely revoke while
 * later batches were still running; allSettled waits for all of them.
 * Then drain ordered offsets so no queued local stores remain before unassign.
 */
export async function awaitRevocationSafety(
    pending: readonly Promise<unknown>[],
    gate: Pick<OffsetCommitGate, 'drain' | 'failed'>
): Promise<{ failedTasks: number; offsetGateFailed: boolean }> {
    const results = await Promise.allSettled(pending)
    await gate.drain()
    return {
        failedTasks: results.filter((result) => result.status === 'rejected').length,
        offsetGateFailed: gate.failed,
    }
}
