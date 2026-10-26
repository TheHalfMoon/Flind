import test from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

import {
    isolatedRustNodeE2E,
    assertIsolatedRustNodeE2EAlreadyPrepared,
    ISOLATED_E2E_ACK,
} from '../../nodejs/tests/service-e2e/rust-node-sandbox-admission.ts'

const valid = () => ({
    FLIND_E2E_DESTRUCTIVE_ACK: ISOLATED_E2E_ACK,
    FLIND_E2E_POSTGRES_BASE_URL: 'postgres://flind:synthetic@127.0.0.1:55432',
    FLIND_E2E_KAFKA_BOOTSTRAP: '127.0.0.1:19092',
    FLIND_E2E_REDIS_URL: 'redis://127.0.0.1:16379',
    FLIND_E2E_CLICKHOUSE_HOST: '127.0.0.1',
    FLIND_E2E_CLICKHOUSE_HTTP_PORT: '18123',
    FLIND_E2E_CLICKHOUSE_DATABASE: 'flind_test_e2e20261026abcd',
})

test('missing explicit destructive sandbox acknowledgement fails before any connection', () => {
    for (const ack of [undefined, '', 'true', 'yes', '1', 'I_OWN_DATABASES']) {
        assert.throws(() => isolatedRustNodeE2E({...valid(), FLIND_E2E_DESTRUCTIVE_ACK:ack}), /explicit disposable/)
    }
})

test('hardcoded shared default PostgreSQL host and port are refused', () => {
    for (const url of [
        'postgres://flind:synthetic@localhost:5432',
        'postgres://flind:synthetic@127.0.0.1:5432',
        'postgres://flind:synthetic@127.0.0.1:55432/posthog',
        'postgres://flind:synthetic@host.example:55432',
        'postgres://flind:synthetic@127.0.0.1:55432/?disable=1',
        'postgres://flind:synthetic@127.0.0.1',
    ]) {
        assert.throws(() => isolatedRustNodeE2E({...valid(), FLIND_E2E_POSTGRES_BASE_URL:url}))
    }
})

test('shared or remote Kafka brokers are refused', () => {
    for (const kafka of ['localhost:9092','127.0.0.1:9092','127.0.0.1:123','10.0.0.5:19092','kafka.example.com:9092','']) {
        assert.throws(() => isolatedRustNodeE2E({...valid(), FLIND_E2E_KAFKA_BOOTSTRAP:kafka}))
    }
})

test('shared Redis ports and remote hosts are refused', () => {
    for (const url of ['redis://127.0.0.1:6379','redis://localhost:16379','redis://10.0.0.1:16379','redis://127.0.0.1:16379/1']) {
        assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_REDIS_URL:url}))
    }
})

test('ClickHouse must use explicit localhost and unique Flind-only test DB name', () => {
    for (const bad of ['posthog_test', 'flind_test_', 'flind_test_short', 'default', 'test_posthog']) {
        assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_CLICKHOUSE_DATABASE:bad}))
    }
    assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_CLICKHOUSE_HOST:'clickhouse.example.com'}))
    for (const port of [undefined, '', '8123', '65536', '123']) {
        assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_CLICKHOUSE_HTTP_PORT:port}))
    }
})

test('service ports must be distinct', () => {
    assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_KAFKA_BOOTSTRAP:'127.0.0.1:55432'}))
    assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_REDIS_URL:'redis://127.0.0.1:19092'}))
    assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_POSTGRES_BASE_URL:'postgres://flind:synthetic@127.0.0.1:8123'}))
    assert.throws(() => isolatedRustNodeE2E({...valid(),FLIND_E2E_POSTGRES_BASE_URL:'postgres://flind:synthetic@127.0.0.1:18123'}))
})

test('safe pre-Jest sandbox expands all distinct test database URLs', () => {
    const result = isolatedRustNodeE2E(valid())
    assert.equal(result.postgresBase,'postgres://flind:synthetic@127.0.0.1:55432')
    assert.equal(result.serviceEnv.DATABASE_URL,'postgres://flind:synthetic@127.0.0.1:55432/test_posthog')
    assert.equal(result.serviceEnv.PERSONS_DATABASE_URL,'postgres://flind:synthetic@127.0.0.1:55432/test_persons')
    assert.equal(result.serviceEnv.CYCLOTRON_NODE_DATABASE_URL,'postgres://flind:synthetic@127.0.0.1:55432/test_cyclotron_node')
    assert.equal(result.serviceEnv.KAFKA_HOSTS,'127.0.0.1:19092')
    assert.equal(result.serviceEnv.CLICKHOUSE_DATABASE,'flind_test_e2e20261026abcd')
    assert.equal(result.serviceEnv.CLICKHOUSE_HTTP_PORT, '18123')
    assert.equal(result.serviceEnv.REDIS_URL,'redis://127.0.0.1:16379')
})

test('direct Jest without early prepared config is refused before destructive beforeAll', () => {
    assert.throws(() => assertIsolatedRustNodeE2EAlreadyPrepared(valid()), /not sandbox-prepared/)
    const base = valid()
    const all = {...base,...isolatedRustNodeE2E(base).serviceEnv}
    assert.equal(assertIsolatedRustNodeE2EAlreadyPrepared(all).clickhouseDatabase,base.FLIND_E2E_CLICKHOUSE_DATABASE)
    assert.throws(() => assertIsolatedRustNodeE2EAlreadyPrepared({...all,DATABASE_URL:'postgres://other@localhost:5432/test_posthog'}))
})

test('CLI wrapper fails safely with missing authorization and never invokes Jest', () => {
    const path = fileURLToPath(new URL('../../nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs',import.meta.url))
    const result = spawnSync(process.execPath,['--no-warnings','--experimental-strip-types',path],
        {encoding:'utf8', env:{PATH:process.env.PATH,HOME:process.env.HOME},timeout:5000})
    assert.equal(result.status,2)
    assert.match(result.stderr,/REFUSED/)
})

test('CLI --dry-run validates without any service or destructive database changes', () => {
    const path = fileURLToPath(new URL('../../nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs',import.meta.url))
    const result = spawnSync(process.execPath,['--no-warnings','--experimental-strip-types',path,'--dry-run'],
        {encoding:'utf8', env:{PATH:process.env.PATH,HOME:process.env.HOME,...valid()},timeout:5000})
    assert.equal(result.status,0)
    assert.match(result.stdout,/no services started or reset/)
    assert.doesNotMatch(result.stdout,/synthetic|55432|19092|flind_test_/)
})
