import { defaultCloudRegion, type RegionId, validateHost } from './regions'

describe('defaultCloudRegion', () => {
    it.each<[string | null, string | null, RegionId | undefined, 'us' | 'eu']>([
        ['DE', 'Europe/Berlin', undefined, 'eu'],
        ['GB', 'Europe/London', undefined, 'eu'],
        ['CY', 'Asia/Nicosia', undefined, 'eu'],
        ['fi', null, undefined, 'eu'],
        ['US', 'America/New_York', undefined, 'us'],
        ['AU', 'Australia/Sydney', undefined, 'us'],
        [null, 'Europe/Paris', undefined, 'eu'],
        [null, null, undefined, 'us'],
        ['DE', 'Europe/Berlin', 'us', 'us'],
        ['US', 'America/New_York', 'eu', 'eu'],
        ['DE', 'Europe/Berlin', 'custom', 'eu'],
    ])('device region %s, timezone %s and saved region %s select %s', (regionCode, timeZone, saved, expected) => {
        expect(defaultCloudRegion(regionCode, timeZone, saved)).toBe(expected)
    })
})

describe('regions', () => {
    const original = {
        usHost: process.env.EXPO_PUBLIC_FLIND_US_HOST,
        euHost: process.env.EXPO_PUBLIC_FLIND_EU_HOST,
        usClient: process.env.EXPO_PUBLIC_FLIND_US_CLIENT_ID,
        euClient: process.env.EXPO_PUBLIC_FLIND_EU_CLIENT_ID,
    }

    afterEach(() => {
        const all = {
            EXPO_PUBLIC_FLIND_US_HOST: original.usHost,
            EXPO_PUBLIC_FLIND_EU_HOST: original.euHost,
            EXPO_PUBLIC_FLIND_US_CLIENT_ID: original.usClient,
            EXPO_PUBLIC_FLIND_EU_CLIENT_ID: original.euClient,
        }
        for (const [key, value] of Object.entries(all)) {
            if (value === undefined) delete process.env[key]
            else process.env[key] = value
        }
        jest.dontMock('@/lib/environment')
    })

    test.each(['production', 'development', 'preview'] as const)('%s configures only Flind-owned OAuth endpoints', (variant) => {
        jest.isolateModules(() => {
            jest.doMock('@/lib/environment', () => ({ ...jest.requireActual('@/lib/environment'), buildVariant: variant }))
            process.env.EXPO_PUBLIC_FLIND_US_HOST = 'https://us.flind.example'
            process.env.EXPO_PUBLIC_FLIND_EU_HOST = 'https://eu.flind.example'
            process.env.EXPO_PUBLIC_FLIND_US_CLIENT_ID = 'flind-us-client'
            process.env.EXPO_PUBLIC_FLIND_EU_CLIENT_ID = 'flind-eu-client'
            const { CLOUD_REGIONS } = jest.requireActual<typeof import('./regions')>('./regions')
            expect(CLOUD_REGIONS.map((r) => [r.host, r.clientId])).toEqual([
                ['https://us.flind.example', 'flind-us-client'],
                ['https://eu.flind.example', 'flind-eu-client'],
            ])
        })
    })

    test.each([
        ['https://us.posthog.com', 'donor host'],
        ['http://us.flind.example', 'plain HTTP'],
        ['https://us.flind.example/path', 'unexpected path'],
        ['https://user:pass@us.flind.example', 'credentials in address'],
    ])('rejects misconfigured cloud endpoint: %s (%s)', (host) => {
        jest.isolateModules(() => {
            process.env.EXPO_PUBLIC_FLIND_US_HOST = host
            process.env.EXPO_PUBLIC_FLIND_US_CLIENT_ID = 'flind-owned-id'
            delete process.env.EXPO_PUBLIC_FLIND_EU_HOST
            delete process.env.EXPO_PUBLIC_FLIND_EU_CLIENT_ID
            const { CLOUD_REGIONS } = jest.requireActual<typeof import('./regions')>('./regions')
            expect(CLOUD_REGIONS).toEqual([])
        })
    })

    test('unconfigured Flind cloud exposes no inherited provider host or OAuth registration', () => {
        jest.isolateModules(() => {
            delete process.env.EXPO_PUBLIC_FLIND_US_HOST
            delete process.env.EXPO_PUBLIC_FLIND_EU_HOST
            delete process.env.EXPO_PUBLIC_FLIND_US_CLIENT_ID
            delete process.env.EXPO_PUBLIC_FLIND_EU_CLIENT_ID
            const { CLOUD_REGIONS } = jest.requireActual<typeof import('./regions')>('./regions')
            expect(CLOUD_REGIONS).toEqual([])
        })
    })

    test.each([
        ['flind.example.com', 'https://flind.example.com'],
        ['https://flind.example.com/project/2/', 'https://flind.example.com'],
        ['http://localhost:8010', 'http://localhost:8010'],
        ['http://127.0.0.1:8000', 'http://127.0.0.1:8000'],
        ['http://[::1]:8010', 'http://[::1]:8010'],
        ['http://[0:0:0:0:0:0:0:1]:8010', 'http://[::1]:8010'],
    ])('accepts %s as %s', (input, host) => {
        expect(validateHost(input)).toEqual({ ok: true, host })
    })

    test.each([
        ['an empty value', '  '],
        ['inherited US cloud', 'https://us.posthog.com'],
        ['inherited EU cloud', 'https://eu.posthog.com'],
        ['inherited origin', 'https://posthog.com'],
        ['inherited development', 'https://app.dev.posthog.dev'],
        ['URL username/password', 'https://user:pwd@flind.example.com'],
        ['plain http to a remote host', 'http://flind.example.com'],
        ['another loopback address outside the native allowlist', 'http://127.0.0.2:8010'],
        ['the emulator host alias', 'http://10.0.2.2:8010'],
        ['a localhost subdomain', 'http://app.localhost:8010'],
        ['an IPv4-mapped IPv6 address', 'http://[::ffff:127.0.0.1]:8010'],
        ['a non-web scheme', 'ftp://flind.example.com'],
        ['a script URL', 'javascript:alert(1)'],
    ])('rejects %s', (_name, input) => {
        expect(validateHost(input)).toMatchObject({ ok: false })
    })

    test.each([
        ['http://localhost:8010', false],
        ['http://127.0.0.1:8000', false],
        ['http://[::1]:8010', false],
        ['https://localhost:8010', true],
    ])('a store build given %s accepts it: %s', (input, ok) => {
        expect(validateHost(input, false)).toMatchObject({ ok })
    })
})
