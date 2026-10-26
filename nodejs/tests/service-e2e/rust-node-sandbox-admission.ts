/**
 * Fail-closed admission for the destructive native Rust → Node → ClickHouse
 * integration test. This suite resets PostgreSQL and ClickHouse test tables.
 * Configuration MUST be supplied before Jest imports the product config.
 * No imports/dependencies: executable with local Node26 TS stripping.
 */

export const ISOLATED_E2E_ACK = 'I_OWN_THESE_DISPOSABLE_FLIND_TEST_DATABASES'

export type IsolatedRustNodeE2E = {
    postgresBase: string
    kafkaBootstrap: string
    redisUrl: string
    clickhouseHost: string
    clickhouseDatabase: string
    serviceEnv: Record<string, string>
}

function localPort(raw: string, service: string, forbiddenPort: number): number {
    const port = Number(raw)
    if (!Number.isInteger(port) || port < 1025 || port > 65535 || port === forbiddenPort) {
        throw new Error(`Unsafe ${service} port: provide a separate, non-default local test service`)
    }
    return port
}

function localUrl(raw: string | undefined, service: string, scheme: string, forbiddenPort: number): URL {
    if (!raw) {
        throw new Error(`Missing isolated ${service} endpoint`)
    }
    let endpoint: URL
    try {
        endpoint = new URL(raw)
    } catch {
        throw new Error(`Invalid isolated ${service} endpoint`)
    }
    if (endpoint.protocol !== `${scheme}:` || endpoint.hostname !== '127.0.0.1' || !endpoint.port) {
        throw new Error(`Unsafe ${service} endpoint: require ${scheme}://127.0.0.1 with explicit port`)
    }
    localPort(endpoint.port, service, forbiddenPort)
    if (endpoint.search || endpoint.hash) {
        throw new Error(`Unsafe ${service} URL query or fragment`)
    }
    return endpoint
}

export function isolatedRustNodeE2E(env: Record<string, string | undefined>): IsolatedRustNodeE2E {
    if (env.FLIND_E2E_DESTRUCTIVE_ACK !== ISOLATED_E2E_ACK) {
        throw new Error('Refusing database resets: explicit disposable Flind E2E acknowledgement required')
    }

    const postgres = localUrl(env.FLIND_E2E_POSTGRES_BASE_URL, 'PostgreSQL', 'postgres', 5432)
    if (postgres.pathname !== '/' && postgres.pathname !== '') {
        throw new Error('PostgreSQL base URL must not select an existing database')
    }
    const postgresBase = postgres.toString().replace(/\/$/, '')

    const kafka = env.FLIND_E2E_KAFKA_BOOTSTRAP ?? ''
    const kafkaMatch = /^127\.0\.0\.1:(\d{4,5})$/.exec(kafka)
    if (!kafkaMatch) {
        throw new Error('Kafka must use an explicit 127.0.0.1 non-default port')
    }
    const kafkaPort = localPort(kafkaMatch[1], 'Kafka', 9092)

    const redis = localUrl(env.FLIND_E2E_REDIS_URL, 'Redis', 'redis', 6379)
    if (redis.pathname !== '' && redis.pathname !== '/' && redis.pathname !== '/0') {
        throw new Error('Redis E2E may only select an isolated default database')
    }

    // The original ClickHouse test helper and product ingestion clients use
    // the fixed HTTP port 8123. Distinct high-entropy *database* name and an
    // explicit ownership acknowledgement protect other project databases.
    if (env.FLIND_E2E_CLICKHOUSE_HOST !== '127.0.0.1') {
        throw new Error('ClickHouse E2E must use 127.0.0.1 (existing helper uses port 8123)')
    }
    const database = env.FLIND_E2E_CLICKHOUSE_DATABASE ?? ''
    if (!/^flind_test_[a-z0-9]{12,}$/.test(database)) {
        throw new Error('ClickHouse E2E database must use a unique flind_test_<12+chars> identity')
    }
    if (new Set([Number(postgres.port), kafkaPort, Number(redis.port), 8123]).size !== 4) {
        throw new Error('Isolated service ports must be distinct')
    }

    const serviceEnv: Record<string, string> = {
        DATABASE_URL: `${postgresBase}/test_posthog`,
        PERSONS_DATABASE_URL: `${postgresBase}/test_persons`,
        PERSONS_READONLY_DATABASE_URL: `${postgresBase}/test_persons`,
        BEHAVIORAL_COHORTS_DATABASE_URL: `${postgresBase}/test_behavioral_cohorts`,
        CYCLOTRON_NODE_DATABASE_URL: `${postgresBase}/test_cyclotron_node`,
        KAFKA_HOSTS: kafka,
        KAFKA_PRODUCER_METADATA_BROKER_LIST: kafka,
        KAFKA_WARPSTREAM_PRODUCER_METADATA_BROKER_LIST: kafka,
        KAFKA_INGESTION_PRODUCER_METADATA_BROKER_LIST: kafka,
        CLICKHOUSE_HOST: '127.0.0.1',
        CLICKHOUSE_DATABASE: database,
        CLICKHOUSE_SECURE: 'false',
        CLICKHOUSE_VERIFY: 'false',
        REDIS_URL: redis.toString(),
        SITE_URL: 'https://example.com',
        OTEL_SDK_DISABLED: 'true',
        DISABLE_OPENTELEMETRY_TRACING: 'true',
    }

    return {
        postgresBase,
        kafkaBootstrap: kafka,
        redisUrl: redis.toString(),
        clickhouseHost: '127.0.0.1',
        clickhouseDatabase: database,
        serviceEnv,
    }
}

/** Refuse a direct Jest invocation whose module-level configs were initialized
 * against unverified inherited endpoints before this suite's beforeAll hook. */
export function assertIsolatedRustNodeE2EAlreadyPrepared(env: Record<string, string | undefined>): IsolatedRustNodeE2E {
    const config = isolatedRustNodeE2E(env)
    for (const [key, expected] of Object.entries(config.serviceEnv)) {
        if (env[key] !== expected) {
            throw new Error(`Refusing destructive E2E: ${key} was not sandbox-prepared before Jest module imports`)
        }
    }
    return config
}
