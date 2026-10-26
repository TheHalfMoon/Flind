/** Fail fast when an isolated destructive E2E reset did not clear its tables.
 * Conventional partial-schema tests keep their historical tolerant behavior.
 * Never include rejected error details here: they may contain credentials.
 */
export function assertIsolatedClickhouseReset(
    settled: ReadonlyArray<PromiseSettledResult<unknown>>,
    phase: number,
    isolatedE2E: boolean
): void {
    if (isolatedE2E && settled.some((result) => result.status === 'rejected')) {
        throw new Error(`Flind isolated ClickHouse reset phase ${phase} failed`)
    }
}
