/**
 * Explicitly admitted service-E2E teardown only.
 *
 * Jest executes afterAll even if beforeAll rejects the sandbox admission.
 * Never invoke destructive database helpers on that path. If admission
 * succeeded, try each independent cleanup stage and always close the client.
 * Error details are deliberately omitted because drivers may include secrets.
 */
export type IsolatedE2EClickhouse = {
    resetTestDatabase(): Promise<void>
    close(): void
}

export async function cleanupAdmittedRustNodeE2E(
    sandboxAdmitted: boolean,
    clickhouse: IsolatedE2EClickhouse | undefined,
    resetPostgres: () => Promise<void>
): Promise<void> {
    if (!sandboxAdmitted || !clickhouse) {
        return
    }

    let failures = 0
    try {
        try {
            await resetPostgres()
        } catch {
            failures++
        }

        try {
            await clickhouse.resetTestDatabase()
        } catch {
            failures++
        }
    } finally {
        try {
            clickhouse.close()
        } catch {
            failures++
        }
    }

    if (failures > 0) {
        throw new Error(`Flind isolated service E2E teardown failed (${failures} cleanup stage(s))`)
    }
}
