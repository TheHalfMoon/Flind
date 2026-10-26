import { beforeEach, describe, expect, it, vi } from 'vitest'

import { handleRegister } from '@/handlers/register'

import { createMockKV } from './helpers'

const mockKV = createMockKV()
const ownedEnv = { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' }

beforeEach(() => {
    vi.clearAllMocks()
})

describe('handleRegister', () => {
    it.each([
        ['missing origins', {}],
        ['inherited vendor', { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com', FLIND_OAUTH_EU_ORIGIN: 'https://eu.posthog.com' }],
        ['same region', { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://us.flind.example' }],
    ])('refuses %s before any fetch or KV write', async (_name, env) => {
        const request = new Request('https://oauth.flind.example/oauth/register/', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
        })
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)
        const result = await handleRegister(request, mockKV, env)
        expect(result.status).toBe(503)
        expect(fetchMock).not.toHaveBeenCalled()
        expect(vi.mocked(mockKV.put)).not.toHaveBeenCalled()
    })

    it('dual-registers on both US and EU, adds proxy callback to redirect_uris, and stores mapping', async () => {
        const usClientId = 'us_client_abc123'
        const euClientId = 'eu_client_def456'
        const sentBodies: Record<string, unknown>[] = []

        vi.stubGlobal(
            'fetch',
            vi.fn().mockImplementation((url: string, init: RequestInit) => {
                sentBodies.push(JSON.parse(init.body as string))
                if (new URL(url).hostname === 'us.flind.example') {
                    return Promise.resolve(
                        new Response(JSON.stringify({ client_id: usClientId, client_name: 'Test App' }), {
                            status: 201,
                            headers: { 'Content-Type': 'application/json' },
                        })
                    )
                }
                return Promise.resolve(
                    new Response(JSON.stringify({ client_id: euClientId, client_name: 'Test App' }), {
                        status: 201,
                        headers: { 'Content-Type': 'application/json' },
                    })
                )
            })
        )

        const request = new Request('https://oauth.flind.example/oauth/register/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: 'Test App', redirect_uris: ['http://localhost:3000/callback'] }),
        })

        const response = await handleRegister(request, mockKV, ownedEnv)
        const data = (await response.json()) as Record<string, unknown>

        expect(response.status).toBe(201)
        expect(data.client_id).toBe(usClientId)

        // Proxy callback URL should be added to redirect_uris sent to both regions
        for (const body of sentBodies) {
            expect(body.redirect_uris).toContain('http://localhost:3000/callback')
            expect(body.redirect_uris).toContain('https://oauth.flind.example/oauth/callback/')
        }

        // Stored mapping should have original redirect_uris (without proxy callback)
        expect(vi.mocked(mockKV.put)).toHaveBeenCalledOnce()
        const storedMapping = JSON.parse(vi.mocked(mockKV.put).mock.calls[0]![1] as string)
        expect(storedMapping.us_client_id).toBe(usClientId)
        expect(storedMapping.eu_client_id).toBe(euClientId)
        expect(storedMapping.redirect_uris).toEqual(['http://localhost:3000/callback'])
    })

    it('returns error when one region fails', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockImplementation((url: string) => {
                if (new URL(url).hostname === 'us.flind.example') {
                    return Promise.resolve(
                        new Response(JSON.stringify({ client_id: 'us_abc', client_name: 'Test' }), {
                            status: 201,
                            headers: { 'Content-Type': 'application/json' },
                        })
                    )
                }
                return Promise.resolve(
                    new Response(JSON.stringify({ error: 'server_error' }), {
                        status: 500,
                        headers: { 'Content-Type': 'application/json' },
                    })
                )
            })
        )

        const request = new Request('https://oauth.flind.example/oauth/register/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: 'Test', redirect_uris: ['http://localhost:3000/callback'] }),
        })

        const response = await handleRegister(request, mockKV, ownedEnv)
        expect(response.status).toBe(500)
        expect(vi.mocked(mockKV.put)).not.toHaveBeenCalled()
    })

    it('returns error when both registrations fail', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockImplementation(() =>
                Promise.resolve(
                    new Response(JSON.stringify({ error: 'invalid_client_metadata' }), {
                        status: 400,
                        headers: { 'Content-Type': 'application/json' },
                    })
                )
            )
        )

        const request = new Request('https://oauth.flind.example/oauth/register/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: '' }),
        })

        const response = await handleRegister(request, mockKV, ownedEnv)
        expect(response.status).toBe(400)
        expect(vi.mocked(mockKV.put)).not.toHaveBeenCalled()
    })
})
