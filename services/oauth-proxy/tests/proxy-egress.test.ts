import { afterEach, describe, expect, it, vi } from 'vitest'

import { proxyPostWithClientId, proxyToRegionAtOrigins, tryBothRegionsAtOrigins } from '@/lib/proxy'

const trusted = { us: 'https://us.flind.example', eu: 'https://eu.flind.example' }
const inherited = { us: 'https://us.posthog.com', eu: 'https://eu.posthog.com' }

afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
})

describe('Flind outbound OAuth proxy egress', () => {
    it('rejects unowned and missing destinations before any network request', async () => {
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)
        const get = () => new Request('https://oauth.flind.example/invoke')
        const post = () => new Request('https://oauth.flind.example/oauth/token/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'client_id=flind_client&client_secret=test',
        })

        expect((await proxyToRegionAtOrigins(get(), 'us', '/oauth/userinfo/', inherited)).status).toBe(503)
        const rewritten = await proxyPostWithClientId(post(), 'eu', '/oauth/token/',
            'flind_client', 'flind_regional_client', undefined, undefined, inherited)
        expect(rewritten.status).toBe(503)
        expect(rewritten.headers.get('cache-control')).toBe('no-store')
        const missing = await proxyPostWithClientId(post(), 'us', '/oauth/token/',
            'flind_client', 'regional_client')
        expect(missing.status).toBe(503)
        const tryBoth = await tryBothRegionsAtOrigins(post(), '/oauth/token/', inherited)
        expect(tryBoth.response.status).toBe(503)
        expect(tryBoth.region).toBeNull()
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('routes direct, rewritten and fallback requests only to explicit owned destinations', async () => {
        const fetchMock = vi.fn()
            .mockResolvedValueOnce(new Response('ok', { status: 200 }))
            .mockResolvedValueOnce(new Response('{}', { status: 200 }))
            .mockResolvedValueOnce(new Response('bad', { status: 400 }))
            .mockResolvedValueOnce(new Response('good', { status: 200 }))
        vi.stubGlobal('fetch', fetchMock)
        await proxyToRegionAtOrigins(new Request('https://oauth.flind.example/a'), 'us', '/oauth/userinfo/', trusted)
        await proxyPostWithClientId(new Request('https://oauth.flind.example/oauth/token/', {
            method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'client_id=flind_client',
        }), 'eu', '/oauth/token/', 'flind_client', 'eu_client', undefined, undefined, trusted)
        const both = await tryBothRegionsAtOrigins(new Request('https://oauth.flind.example/oauth/token/', {
            method: 'POST', body: 'grant_type=refresh_token',
        }), '/oauth/token/', trusted)

        expect(both.region).toBe('eu')
        expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
            'https://us.flind.example/oauth/userinfo/',
            'https://eu.flind.example/oauth/token/',
            'https://us.flind.example/oauth/token/',
            'https://eu.flind.example/oauth/token/',
        ])
        const form = new URLSearchParams(fetchMock.mock.calls[1]?.[1]?.body as string)
        expect(form.get('client_id')).toBe('eu_client')
    })
})
