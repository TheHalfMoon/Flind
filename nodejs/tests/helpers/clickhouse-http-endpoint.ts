/** Shared test ClickHouse HTTP origin, used by the original client and health probe.
 * A dedicated FLIND_E2E sandbox supplies an isolated nondefault port;
 * legacy project tests without an override keep ClickHouse's 8123 default.
 * No runtime imports: can be tested directly with native Node.
 */
export function clickhouseTestHttpOrigin(env: Record<string, string | undefined>): string {
    const host = env.CLICKHOUSE_HOST ?? 'localhost'
    const portRaw = env.CLICKHOUSE_HTTP_PORT ?? '8123'
    const port = Number(portRaw)
    if (!/^\d{4,5}$/.test(portRaw) || !Number.isInteger(port) || port <= 1024 || port > 65535) {
        throw new Error('Invalid ClickHouse HTTP test port')
    }
    if (!/^[a-z0-9.-]+$/i.test(host) || host.includes('..')) {
        throw new Error('Invalid ClickHouse test host')
    }
    return `http://${host}:${port}`
}
