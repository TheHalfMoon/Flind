import { exportPKCS8, generateKeyPair } from 'jose'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { handleJwks } from '@/handlers/passthrough'

const kv = {} as KVNamespace
const request = () => new Request('https://oauth.flind.example/.well-known/jwks.json')
const regionEnv = { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' }

async function makeSigningPem(): Promise<string> {
    const { privateKey } = await generateKeyPair('RS256', { extractable: true })
    return exportPKCS8(privateKey)
}

afterEach(() => vi.unstubAllGlobals())

describe('Flind-owned regional JWKS cache and identity', () => {
    it('refuses missing and inherited regional origins before any HTTP', async () => {
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)
        for (const env of [
            {},
            { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com', FLIND_OAUTH_EU_ORIGIN: 'https://eu.posthog.com' },
            { FLIND_OAUTH_US_ORIGIN: regionEnv.FLIND_OAUTH_US_ORIGIN, FLIND_OAUTH_EU_ORIGIN: regionEnv.FLIND_OAUTH_US_ORIGIN },
        ]) {
            const response = await handleJwks(request(), kv, env)
            expect(response.status).toBe(503)
            expect(response.headers.get('Cache-Control')).toBe('no-store')
        }
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('isolates JWKS cache after a first-party region changes', async () => {
        const fetchMock = vi.fn(async (url: string) => {
            const region = new URL(url).hostname
            return new Response(JSON.stringify({
                keys: [{ kty: 'RSA', kid: region, n: 'test-only-key', e: 'AQAB' }],
            }), { status: 200 })
        })
        vi.stubGlobal('fetch', fetchMock)
        const env = { ...regionEnv }
        const first = await handleJwks(request(), kv, env)
        expect(first.status).toBe(200)
        const initial = (await first.json()) as { keys: Array<{ kid: string }> }
        expect(initial.keys.map((key) => key.kid)).toContain('us.flind.example')
        expect(fetchMock).toHaveBeenCalledTimes(2)

        await handleJwks(request(), kv, env)
        expect(fetchMock).toHaveBeenCalledTimes(2)

        const changed = { ...env, FLIND_OAUTH_US_ORIGIN: 'https://us2.flind.example' }
        const second = await handleJwks(request(), kv, changed)
        expect(second.status).toBe(200)
        const rewritten = (await second.json()) as { keys: Array<{ kid: string }> }
        expect(rewritten.keys.map((key) => key.kid)).toContain('us2.flind.example')
        expect(rewritten.keys.map((key) => key.kid)).not.toContain('us.flind.example')
        expect(fetchMock).toHaveBeenCalledTimes(4)
        for (const [url] of fetchMock.mock.calls) {
            expect(url).not.toContain('posthog.com')
        }
    })

    it('invalidates cached JWKS when the active Flind signing PEM is rotated', async () => {
        const signingA = await makeSigningPem()
        const signingB = await makeSigningPem()
        const fetchMock = vi.fn(async (url: string) =>
            new Response(JSON.stringify({
                keys: [{ kty: 'RSA', kid: new URL(url).hostname, n: 'test-only-key', e: 'AQAB' }],
            }), { status: 200 })
        )
        vi.stubGlobal('fetch', fetchMock)

        const first = await handleJwks(request(), kv, { ...regionEnv, OIDC_SIGNING_KEY: signingA })
        const firstKids = ((await first.json()) as { keys: Array<{ kid: string }> }).keys.map((key) => key.kid)
        expect(firstKids).toHaveLength(3)
        expect(fetchMock).toHaveBeenCalledTimes(2)

        const second = await handleJwks(request(), kv, { ...regionEnv, OIDC_SIGNING_KEY: signingB })
        const rotatedKids = ((await second.json()) as { keys: Array<{ kid: string }> }).keys.map((key) => key.kid)
        expect(rotatedKids).toHaveLength(3)
        expect(rotatedKids[0]).not.toBe(firstKids[0])
        expect(fetchMock).toHaveBeenCalledTimes(4)
    })
})
