import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { cleanupAdmittedRustNodeE2E } from '../../nodejs/tests/service-e2e/isolated-e2e-teardown.ts'

function fixture({ postgresFails = false, clickhouseFails = false, closeFails = false } = {}) {
    const steps = []
    const client = {
        async resetTestDatabase() {
            steps.push('clickhouse')
            if (clickhouseFails) throw Error('CH_SECRET')
        },
        close() {
            steps.push('close')
            if (closeFails) throw Error('CLOSE_SECRET')
        },
    }
    const postgres = async () => {
        steps.push('postgres')
        if (postgresFails) throw Error('PG_SECRET')
    }
    return { steps, client, postgres }
}

const denied = fixture()
await cleanupAdmittedRustNodeE2E(false, undefined, denied.postgres)
assert.deepEqual(denied.steps, [])

const deniedWithClient = fixture()
await cleanupAdmittedRustNodeE2E(false, deniedWithClient.client, deniedWithClient.postgres)
assert.deepEqual(deniedWithClient.steps, [])

const successful = fixture()
await cleanupAdmittedRustNodeE2E(true, successful.client, successful.postgres)
assert.deepEqual(successful.steps, ['postgres', 'clickhouse', 'close'])

for (const bad of ['postgresFails', 'clickhouseFails', 'closeFails']) {
    const args = { [bad]: true }
    const failed = fixture(args)
    await assert.rejects(
        cleanupAdmittedRustNodeE2E(true, failed.client, failed.postgres),
        (error) => error instanceof Error &&
            error.message.includes('Flind isolated service E2E teardown failed') &&
            !/PG_SECRET|CH_SECRET|CLOSE_SECRET/.test(error.message)
    )
    assert.deepEqual(failed.steps, ['postgres', 'clickhouse', 'close'])
}

const multiple = fixture({ postgresFails: true, clickhouseFails: true, closeFails: true })
await assert.rejects(
    cleanupAdmittedRustNodeE2E(true, multiple.client, multiple.postgres),
    /3 cleanup stage\(s\)/
)
assert.deepEqual(multiple.steps, ['postgres', 'clickhouse', 'close'])

// Ensure the real first-party Jest fixture uses this guard after validating
// the exact prepared sandbox, rather than merely having an unused helper.
const source = readFileSync(new URL('../../nodejs/tests/service-e2e/rust-ingestion-consumer.serial.test.ts', import.meta.url), 'utf8')
const admission = source.indexOf('        configureParentTestEnv()')
const allowed = source.indexOf('        sandboxAdmitted = true')
const afterAll = source.indexOf('cleanupAdmittedRustNodeE2E(sandboxAdmitted, clickhouse, resetTestDatabase)')
assert.ok(admission >= 0 && allowed > admission && afterAll > allowed)
assert.equal((source.match(/\bawait resetTestDatabase\(\)/g) ?? []).length, 1)
console.log('Wave131 PASS: denied sandbox cannot reset DB; admitted cleanup always closes (7 scenarios)')
