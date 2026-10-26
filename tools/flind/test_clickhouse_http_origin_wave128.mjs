import test from 'node:test'
import assert from 'node:assert/strict'
import { clickhouseTestHttpOrigin } from '../../nodejs/tests/helpers/clickhouse-http-endpoint.ts'

test('default local first-party test origin stays backwards-compatible', () => {
    assert.equal(clickhouseTestHttpOrigin({}), 'http://localhost:8123')
})
test('a private loopback HTTP override is exact and non-default', () => {
    assert.equal(clickhouseTestHttpOrigin({
        CLICKHOUSE_HOST: '127.0.0.1',
        CLICKHOUSE_HTTP_PORT: '18123',
    }), 'http://127.0.0.1:18123')
})
test('upper valid port bound is retained exactly', () => {
    assert.equal(clickhouseTestHttpOrigin({
        CLICKHOUSE_HOST: '127.0.0.1',
        CLICKHOUSE_HTTP_PORT: '65535',
    }), 'http://127.0.0.1:65535')
})
test('invalid port formats and out-of-range ports fail closed', () => {
    for (const port of ['0', '65536', '1000', '123', '-18123', '1e4', '18123/query', '18123?x=1', ' 18123']) {
        assert.throws(() => clickhouseTestHttpOrigin({
            CLICKHOUSE_HOST: '127.0.0.1',
            CLICKHOUSE_HTTP_PORT: port,
        }), /Invalid ClickHouse HTTP test port/)
    }
})
test('untrusted malformed host strings fail closed', () => {
    for (const host of ['127.0.0.1/path', 'user@127.0.0.1', '127.0.0.1?x=1',
        '127.0.0.1:8123', 'evil..example', '[::1]', '127.0.0.1%0a']) {
        assert.throws(() => clickhouseTestHttpOrigin({
            CLICKHOUSE_HOST: host,
            CLICKHOUSE_HTTP_PORT: '18123',
        }), /Invalid ClickHouse test host/)
    }
})
test('sandbox uses same ClickHouse endpoint for real query and health probe', async () => {
    const fs = await import('node:fs/promises')
    const server = await fs.readFile(new URL('../../nodejs/tests/helpers/clickhouse.ts', import.meta.url), 'utf8')
    assert.match(server, /url: clickhouseTestHttpOrigin\(process.env\)/)
    assert.match(server, /fetch\(\x60\$\{clickhouseTestHttpOrigin\(process.env\)\}\/ping\x60\)/)
    assert.doesNotMatch(server, /http:\/\/localhost:8123\/ping/)
})
