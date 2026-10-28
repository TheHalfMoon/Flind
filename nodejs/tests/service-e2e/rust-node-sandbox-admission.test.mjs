import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
    ISOLATED_E2E_ACK,
    isolatedRustNodeE2E,
    selectTestClickhouseDatabase,
} from './rust-node-sandbox-admission.ts'

function sandboxEnv() {
    const request = {
        FLIND_E2E_DESTRUCTIVE_ACK: ISOLATED_E2E_ACK,
        FLIND_E2E_POSTGRES_BASE_URL: 'postgres://test:test@127.0.0.1:15439',
        FLIND_E2E_KAFKA_BOOTSTRAP: '127.0.0.1:19093',
        FLIND_E2E_REDIS_URL: 'redis://127.0.0.1:16380',
        FLIND_E2E_CLICKHOUSE_HOST: '127.0.0.1',
        FLIND_E2E_CLICKHOUSE_HTTP_PORT: '18124',
        FLIND_E2E_CLICKHOUSE_DATABASE: 'flind_test_abc123abc123',
    }
    const admitted = isolatedRustNodeE2E(request)
    return { ...request, ...admitted.serviceEnv }
}

test('non-service Jest suites retain the ordinary test database', () => {
    assert.equal(selectTestClickhouseDatabase({ NODE_ENV: 'test' }), 'posthog_test')
    assert.equal(selectTestClickhouseDatabase({ CLICKHOUSE_DATABASE: 'production' }), 'posthog_test')
})

test('admitted service E2E keeps the unique Flind ClickHouse identity', () => {
    const env = sandboxEnv()
    assert.equal(selectTestClickhouseDatabase(env), env.FLIND_E2E_CLICKHOUSE_DATABASE)
})

test('tampered ClickHouse target aborts before test setup can import a database', () => {
    const env = sandboxEnv()
    env.CLICKHOUSE_DATABASE = 'posthog_test'
    assert.throws(() => selectTestClickhouseDatabase(env), /not sandbox-prepared/)
})

test('missing service acknowledgement cannot select a database', () => {
    const env = sandboxEnv()
    delete env.FLIND_E2E_DESTRUCTIVE_ACK
    assert.throws(() => selectTestClickhouseDatabase(env), /acknowledgement/)
})

test('partial Flind service environment is refused, not silently defaulted', () => {
    assert.throws(
        () => selectTestClickhouseDatabase({ FLIND_E2E_CLICKHOUSE_DATABASE: 'flind_test_abc123abc123' }),
        /acknowledgement/
    )
})
