import { afterEach, describe, expect, it, vi } from 'vitest'

import { handleIntrospect, handleUserInfo } from '@/handlers/passthrough'

const kv = {} as KVNamespace
const ownedEnv = {
    FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
    FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example',
}

afterEach(() => vi.unstubAllGlobals())

describe('Flind-owned UserInfo and introspection backends', () => {
    it.each([
        ['missing', {}],
        ['original hosts', { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com', FLIND_OAUTH_EU_ORIGIN: 'https://eu.posthog.com' }],
        ['same region', { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://us.flind.example' }],
        ['unowned HTTP', { FLIND_OAUTH_US_ORIGIN: 'http://us.flind.example', FLIND_OAUTH_EU_ORIGIN: ownedEnv.FLIND_OAUTH_EU_ORIGIN }],
    ])('refuses %s before any HTTP on BOTH endpoint types', async (_label, env) => {
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)

        const introspection = await handleIntrospect(
            new Request('https://oauth.flind.example/oauth/introspect/', {
                method: 'POST', body: 'token=fake-token', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            }),
            kv, env
        )
        expect(introspection.status).toBe(503)
        expect(introspection.headers.get('Cache-Control')).toBe('no-store')

        const userInfo = await handleUserInfo(new Request('https://oauth.flind.example/oauth/userinfo/', {
            method: 'POST', body: 'token=fake-token',
        }), kv, env)
        expect(userInfo.status).toBe(503)
        expect(userInfo.headers.get('Cache-Control')).toBe('no-store')
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('proxies introspection only to owned US when its token is active', async () => {
        const fetchMock = vi.fn().mockResolvedValueOnce(
            new Response(JSON.stringify({ active: true, sub: 'flind-user' }), {
                status: 200, headers: { 'Content-Type': 'application/json' },
            })
        )
        vi.stubGlobal('fetch', fetchMock)
        const response = await handleIntrospect(new Request('https://oauth.flind.example/oauth/introspect/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': '42' },
            body: 'token=fake-token',
        }), kv, ownedEnv)
        expect(response.status).toBe(200)
        expect(await response.json()).toEqual({ active: true, sub: 'flind-user' })
        expect(fetchMock).toHaveBeenCalledTimes(1)
        expect(fetchMock.mock.calls[0]?.[0]).toBe('https://us.flind.example/oauth/introspect/')
    })

    it('uses owned EU only after US returns an inactive token', async () => {
        const fetchMock = vi.fn()
            .mockResolvedValueOnce(new Response(JSON.stringify({ active: false }), { status: 200 }))
            .mockResolvedValueOnce(new Response(JSON.stringify({ active: true, sub: 'eu-user' }), { status: 200, headers: { 'Cache-Control': 'public, max-age=3600' } }))
        vi.stubGlobal('fetch', fetchMock)
        const response = await handleIntrospect(new Request('https://oauth.flind.example/oauth/introspect/', {
            method: 'POST', body: 'token=eu-test',
        }), kv, ownedEnv)
        expect(await response.json()).toEqual({ active: true, sub: 'eu-user' })
        expect(response.headers.get('cache-control')).toBe('no-store')
        expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
            'https://us.flind.example/oauth/introspect/',
            'https://eu.flind.example/oauth/introspect/',
        ])
    })

    it('routes UserInfo to owned EU after an unsuccessful US response', async () => {
        const fetchMock = vi.fn()
            .mockResolvedValueOnce(new Response(JSON.stringify({ error: 'invalid_token' }), { status: 401 }))
            .mockResolvedValueOnce(new Response(JSON.stringify({ sub: 'eu-owned-user' }), { status: 200, headers: { 'Cache-Control': 'public, max-age=3600' } }))
        vi.stubGlobal('fetch', fetchMock)
        const request = new Request('https://oauth.flind.example/oauth/userinfo/', {
            method: 'POST', headers: { Authorization: 'Bearer fake-eu-token' }, body: '',
        })
        const response = await handleUserInfo(request, kv, ownedEnv)
        expect(await response.json()).toEqual({ sub: 'eu-owned-user' })
        expect(response.headers.get('cache-control')).toBe('no-store')
        expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
            'https://us.flind.example/oauth/userinfo/',
            'https://eu.flind.example/oauth/userinfo/',
        ])
        for (const [url, init] of fetchMock.mock.calls) {
            expect(url).not.toContain('posthog.com')
            expect(init.headers.get('authorization')).toBe('Bearer fake-eu-token')
        }
    })
})
