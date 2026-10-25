import type { OffsetCommitGate } from './offset-commit-gate'

/**
 * Drain every pending event batch and ordered offset store before closing
 * the native Kafka consumer. Retain original processing failures as well
 * as teardown errors. A failed store must never be reported as clean exit.
 */
export async function drainAndDisconnectConsumer(
    pending: readonly Promise<unknown>[],
    gate: Pick<OffsetCommitGate, 'drain' | 'failed'>,
    disconnect: () => Promise<void>,
    primaryError?: unknown
): Promise<void> {
    const failures: unknown[] = primaryError === undefined ? [] : [primaryError]
    const results = await Promise.allSettled(pending)
    for (const result of results) {
        if (result.status === 'rejected' && !failures.includes(result.reason)) {
            failures.push(result.reason)
        }
    }
    try {
        await gate.drain()
    } catch (error) {
        if (!failures.includes(error)) {
            failures.push(error)
        }
    }
    if (gate.failed && failures.length === 0) {
        failures.push(new Error('Kafka background work or offset store failed during consumer loop cleanup'))
    }
    try {
        await disconnect()
    } catch (error) {
        if (!failures.includes(error)) {
            failures.push(error)
        }
    }
    if (failures.length === 1) {
        throw failures[0]
    }
    if (failures.length > 1) {
        throw new AggregateError(failures, 'Kafka consumer loop and cleanup failed')
    }
}
