import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { assertIsolatedClickhouseReset } from '../../nodejs/tests/helpers/clickhouse-reset-guard.ts'

const ok = [{ status: 'fulfilled', value: undefined }]
const failure = [...ok, { status: 'rejected', reason: new Error('PRIVATE_PASSWORD') }]

assert.doesNotThrow(() => assertIsolatedClickhouseReset(ok, 1, true))
assert.doesNotThrow(() => assertIsolatedClickhouseReset(failure, 2, false))
assert.throws(
    () => assertIsolatedClickhouseReset(failure, 2, true),
    (error) => error instanceof Error &&
        error.message === 'Flind isolated ClickHouse reset phase 2 failed' &&
        !error.message.includes('PRIVATE_PASSWORD')
)

const source = readFileSync(new URL('../../nodejs/tests/helpers/clickhouse.ts', import.meta.url), 'utf8')
assert.equal((source.match(/assertIsolatedClickhouseReset\(phase\d,/g) ?? []).length, 3)
assert.ok(source.includes('FLIND_E2E_DESTRUCTIVE_ACK'))
console.log('Wave130 PASS: ClickHouse E2E reset failure is visible and sanitized')
