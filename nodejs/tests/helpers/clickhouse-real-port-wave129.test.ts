import { Clickhouse } from './clickhouse'

describe('Wave129 actual first-party Clickhouse client and isolated HTTP server', () => {
    it('reads an owned temporary database on a non-default port', async () => {
        const expectedPort = process.env.FLIND_W129_CLICKHOUSE_HTTP_PORT
        const expectedDatabase = process.env.FLIND_W129_CLICKHOUSE_DATABASE
        if (!expectedPort || expectedPort === '8123' || !/^\d{4,5}$/.test(expectedPort)) {
            throw new Error('Owned private nondefault ClickHouse port required')
        }
        if (!expectedDatabase || !/^flind_test_[a-z0-9]{12,}$/.test(expectedDatabase)) {
            throw new Error('Unique owned temporary Flind ClickHouse database required')
        }
        // Original Jest setup defaults to posthog_test. Override only within
        // this disposable test before the real client is constructed; the
        // private HTTP server contains exclusively the owned Flind database.
        process.env.CLICKHOUSE_HOST = '127.0.0.1'
        process.env.CLICKHOUSE_HTTP_PORT = expectedPort
        process.env.CLICKHOUSE_DATABASE = expectedDatabase
        const client = Clickhouse.create()
        try {
            const db = await client.query<{ name: string }>('SELECT currentDatabase() AS name')
            expect(db.map((item) => item.name)).toEqual([expectedDatabase])
            const data = await client.query<{ count: number; sum: number }>(
                'SELECT count() AS count, sum(value) AS sum FROM flind_private_probe'
            )
            expect(data).toEqual([{ count: 3, sum: 60 }])
        } finally {
            client.close()
        }
    })
})
