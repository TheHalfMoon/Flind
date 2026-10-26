import { afterEach, describe, expect, it, vi } from 'vitest'

import { handleRevoke } from '@/handlers/passthrough'
import { putClientMapping, putRegionSelection } from '@/lib/kv'

import { createInMemoryKV } from './helpers'

const owned = { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' }

afterEach(() => vi.unstubAllGlobals())

function revokeRequest(clientId: string): Request {
    return new Request('https://oauth.flind.example/oauth/revoke/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ client_id: clientId, token: 'synthetic-only-token' }).toString(),
    })
}

describe('Flind-owned regional OAuth revocation', () => {
    it.each([
        ['missing', {}],
        ['vendor', { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com', FLIND_OAUTH_EU_ORIGIN: 'https://eu.posthog.com' }],
        ['duplicate', { FLIND_OAUTH_US_ORIGIN: owned.FLIND_OAUTH_US_ORIGIN, FLIND_OAUTH_EU_ORIGIN: owned.FLIND_OAUTH_US_ORIGIN }],
    ])('refuses %s regions before KV access or network', async (_label, env) => {
        const kv = { get: vi.fn(), put: vi.fn() } as unknown as KVNamespace
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)
        const response = await handleRevoke(revokeRequest('client-a'), kv, env)
        expect(response.status).toBe(503)
        expect(response.headers.get('Cache-Control')).toBe('no-store')
        expect(fetchMock).not.toHaveBeenCalled()
        expect(vi.mocked(kv.get)).not.toHaveBeenCalled()
    })

    it('rewrites an EU-mapped client ID and revokes only against owned EU', async () => {
        const kv = createInMemoryKV()
        await putClientMapping(kv, 'proxy-client', {
            us_client_id: 'us-owned-client', eu_client_id: 'eu-owned-client',
            redirect_uris: [], created_at: Date.now(),
        })
        await putRegionSelection(kv, 'proxy-client', 'eu')
        const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }))
        vi.stubGlobal('fetch', fetchMock)
        const response = await handleRevoke(revokeRequest('proxy-client'), kv, owned)
        expect(response.status).toBe(200)
        expect(fetchMock).toHaveBeenCalledTimes(1)
        expect(fetchMock.mock.calls[0]?.[0]).toBe('https://eu.flind.example/oauth/revoke/')
        const params = new URLSearchParams(fetchMock.mock.calls[0]?.[1].body as string)
        expect(params.get('client_id')).toBe('eu-owned-client')
        expect(params.get('token')).toBe('synthetic-only-token')
    })

    it('tries only owned US then EU if a client has no region mapping', async () => {
        const kv = createInMemoryKV()
        const fetchMock = vi.fn()
            .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'invalid_token' }), { status: 400 }))
            .mockResolvedValueOnce(new Response(null, { status: 200 }))
        vi.stubGlobal('fetch', fetchMock)
        const response = await handleRevoke(revokeRequest('unknown-client'), kv, owned)
        expect(response.status).toBe(200)
        expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
            'https://us.flind.example/oauth/revoke/',
            'https://eu.flind.example/oauth/revoke/',
        ])
    })
})
