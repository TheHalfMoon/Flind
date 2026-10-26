import assert from 'node:assert/strict'
import { clickhouseTestHttpOrigin } from '../../nodejs/tests/helpers/clickhouse-http-endpoint.ts'

// Executes the exact endpoint-origin builder used by the real first-party Node
// Clickhouse test helper. The server and database are ephemeral and private.
const port = process.env.FLIND_W128_CLICKHOUSE_HTTP_PORT
const database = process.env.FLIND_W128_CLICKHOUSE_DATABASE

assert.match(port ?? '', /^\d{4,5}$/)
assert.notEqual(port, '8123')
assert.match(database ?? '', /^flind_test_[a-z0-9]{12,}$/)

const url = clickhouseTestHttpOrigin({
    CLICKHOUSE_HOST: '127.0.0.1',
    CLICKHOUSE_HTTP_PORT: port,
})
assert.equal(url, `http://127.0.0.1:${port}`)

async function query(sql) {
    const response = await fetch(`${url}/?database=${encodeURIComponent(database)}`, {
        method: 'POST',
        headers: {'Content-Type': 'text/plain'},
        body: sql,
        signal: AbortSignal.timeout(4500),
    })
    assert.equal(response.status, 200, 'Real isolated ClickHouse query failed')
    return await response.text()
}
assert.equal((await query('SELECT currentDatabase()')).trim(), database)
const received = (await query('SELECT count(), sum(value) FROM flind_private_probe')).trim()
assert.equal(received, '3\t60')

process.stdout.write(JSON.stringify({
    first_party_clickhouse_origin_exercised: true,
    isolated_real_clickhouse_sql_readback: true,
    observed_rows: 3,
    observed_sum: 60,
    original_clickhouse_helper_full_runtime_loaded: false,
    release_qualified: false,
}) + '\n')
