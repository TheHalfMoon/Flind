import { SignJWT, type JWK, decodeJwt, exportJWK, exportPKCS8, generateKeyPair, importJWK, jwtVerify } from 'jose'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { handleJwks } from '@/handlers/passthrough'
import { IdTokenReissueError, reissueIdToken } from '@/lib/idtoken'

import { createMockKV } from './helpers'

// Relative to now, so the fixture keeps describing a live token however long this test lives.
const ISSUED_AT = Math.floor(Date.now() / 1000)
const EXPIRES_AT = ISSUED_AT + 3600

const REGIONAL_CLIENT_ID = 'us_regional_client_id'
const ownedFlindRegions = { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' }

interface RegionalKey {
    privateKey: CryptoKey
    publicJwk: JWK
}

async function createRegionalKey(): Promise<RegionalKey> {
    const { privateKey, publicKey } = await generateKeyPair('RS256', { extractable: true })
    return { privateKey, publicJwk: await exportJWK(publicKey) }
}

async function createProxyKeyPem(): Promise<string> {
    const { privateKey } = await generateKeyPair('RS256', { extractable: true })
    return exportPKCS8(privateKey)
}

async function signRegionalIdToken(
    key: RegionalKey,
    claims: Record<string, unknown> = {},
    issuer = 'https://us.flind.example'
): Promise<string> {
    return new SignJWT({
        email: 'someone@example.com',
        email_verified: true,
        nonce: 'nonce-from-the-client',
        at_hash: 'at-hash-of-the-access-token',
        ...claims,
    })
        .setProtectedHeader({ alg: 'RS256' })
        .setIssuer(issuer)
        .setSubject('018f0000-0000-7000-8000-000000000000')
        .setAudience(REGIONAL_CLIENT_ID)
        .setIssuedAt(ISSUED_AT)
        .setExpirationTime(EXPIRES_AT)
        .sign(key.privateKey)
}

function stubRegionalJwks(key: RegionalKey): void {
    // A fresh Response per call: the JWKS handler reads both regions, and a body can be read once.
    vi.stubGlobal(
        'fetch',
        vi.fn(() =>
            Promise.resolve(
                new Response(JSON.stringify({ keys: [key.publicJwk] }), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' },
                })
            )
        )
    )
}

describe('ID token re-issuance', () => {
    let regionalKey: RegionalKey
    let signingKey: string

    // One key set per file: `reissueIdToken` caches the remote JWKS per region, as a worker
    // isolate does, so a fresh key per test would be rejected by the cached set.
    beforeAll(async () => {
        regionalKey = await createRegionalKey()
        signingKey = await createProxyKeyPem()
    })

    beforeEach(() => {
        stubRegionalJwks(regionalKey)
    })

    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('denies missing owned issuer configuration before JWKS network access', async () => {
        const idToken = await signRegionalIdToken(regionalKey)
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)
        await expect(reissueIdToken(idToken, {
            region: 'us', issuer: 'https://oauth.flind.example',
            audience: 'proxy_client_id', permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
            env: { OIDC_SIGNING_KEY: signingKey },
        })).rejects.toThrow('regional issuer trust is not configured')
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('rejects a legitimately signed upstream JWT bearing the wrong issuer', async () => {
        const idToken = await signRegionalIdToken(regionalKey, {}, 'https://unowned.example')
        await expect(reissueIdToken(idToken, {
            region: 'us', issuer: 'https://oauth.flind.example',
            audience: 'proxy_client_id', permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
            env: { ...ownedFlindRegions, OIDC_SIGNING_KEY: signingKey },
        })).rejects.toBeInstanceOf(IdTokenReissueError)
    })

    it('does not reuse a regional JWKS cache after its Flind origin changes', async () => {
        const alternateKey = await createRegionalKey()
        const alternateOrigin = 'https://us.new-owner.flind.example'
        stubRegionalJwks(alternateKey)
        const fetchMock = vi.mocked(fetch)
        const idToken = await signRegionalIdToken(alternateKey, {}, alternateOrigin)
        const reissued = await reissueIdToken(idToken, {
            region: 'us', issuer: 'https://oauth.flind.example',
            audience: 'proxy_client_id', permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
            env: { ...ownedFlindRegions, FLIND_OAUTH_US_ORIGIN: alternateOrigin, OIDC_SIGNING_KEY: signingKey },
        })
        expect(decodeJwt(reissued).aud).toBe('proxy_client_id')
        expect(fetchMock.mock.calls.some((call) => String(call[0]).startsWith(alternateOrigin))).toBe(true)
    })

    it('replaces the regional issuer and audience while preserving the identity claims', async () => {
        const idToken = await signRegionalIdToken(regionalKey)

        const reissued = await reissueIdToken(idToken, {
            region: 'us',
            issuer: 'https://oauth.flind.example',
            audience: 'proxy_client_id',
            permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
            env: { ...ownedFlindRegions, OIDC_SIGNING_KEY: signingKey },
        })

        const claims = decodeJwt(reissued)
        expect(claims.iss).toBe('https://oauth.flind.example')
        expect(claims.aud).toBe('proxy_client_id')
        expect(claims.sub).toBe('018f0000-0000-7000-8000-000000000000')
        expect(claims.email).toBe('someone@example.com')
        expect(claims.email_verified).toBe(true)
        expect(claims.nonce).toBe('nonce-from-the-client')
        expect(claims.at_hash).toBe('at-hash-of-the-access-token')
    })

    it('copies the lifetime of the regional token rather than extending it', async () => {
        const idToken = await signRegionalIdToken(regionalKey)

        const reissued = await reissueIdToken(idToken, {
            region: 'us',
            issuer: 'https://oauth.flind.example',
            audience: 'proxy_client_id',
            permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
            env: { ...ownedFlindRegions, OIDC_SIGNING_KEY: signingKey },
        })

        const claims = decodeJwt(reissued)
        expect(claims.iat).toBe(ISSUED_AT)
        expect(claims.exp).toBe(EXPIRES_AT)
    })

    it('signs with a key published in the proxy JWKS', async () => {
        const idToken = await signRegionalIdToken(regionalKey)
        const reissued = await reissueIdToken(idToken, {
            region: 'us',
            issuer: 'https://oauth.flind.example',
            audience: 'proxy_client_id',
            permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
            env: { ...ownedFlindRegions, OIDC_SIGNING_KEY: signingKey },
        })

        const response = await handleJwks(
            new Request('https://oauth.flind.example/.well-known/jwks.json'),
            createMockKV(),
            {
                OIDC_SIGNING_KEY: signingKey,
                FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
                FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example',
            }
        )
        const { keys } = (await response.json()) as { keys: JWK[] }
        const header = JSON.parse(atob(reissued.split('.')[0]!)) as { kid: string }
        const signingJwk = keys.find((key) => key.kid === header.kid)

        expect(signingJwk).not.toBeUndefined()
        await expect(jwtVerify(reissued, await importJWK(signingJwk!, 'RS256'))).resolves.toBeDefined()
    })

    it('keeps publishing the regional keys, which sign ID-JAG access tokens', async () => {
        const response = await handleJwks(
            new Request('https://oauth.flind.example/.well-known/jwks.json'),
            createMockKV(),
            {
                OIDC_SIGNING_KEY: signingKey,
                FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
                FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example',
            }
        )

        const { keys } = (await response.json()) as { keys: JWK[] }
        expect(keys.some((key) => key.n === regionalKey.publicJwk.n)).toBe(true)
    })

    it('refuses to sign without a configured key', async () => {
        const idToken = await signRegionalIdToken(regionalKey)

        await expect(
            reissueIdToken(idToken, {
                region: 'us',
                issuer: 'https://oauth.flind.example',
                audience: 'proxy_client_id',
                permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
                env: {},
            })
        ).rejects.toBeInstanceOf(IdTokenReissueError)
    })

    it('refuses to sign a token the region did not sign', async () => {
        const impostorKey = await createRegionalKey()
        const idToken = await signRegionalIdToken(impostorKey)

        await expect(
            reissueIdToken(idToken, {
                region: 'us',
                issuer: 'https://oauth.flind.example',
                audience: 'proxy_client_id',
                permittedUpstreamAudiences: [REGIONAL_CLIENT_ID],
                env: { ...ownedFlindRegions, OIDC_SIGNING_KEY: signingKey },
            })
        ).rejects.toBeInstanceOf(IdTokenReissueError)
    })

    it('refuses to address a token to a client the region did not issue it to', async () => {
        // Signing the posted client_id over another client's grant forges an identity for it.
        const idToken = await signRegionalIdToken(regionalKey)

        await expect(
            reissueIdToken(idToken, {
                region: 'us',
                issuer: 'https://oauth.flind.example',
                audience: 'victim_client_id',
                permittedUpstreamAudiences: ['victim_client_id'],
                env: { ...ownedFlindRegions, OIDC_SIGNING_KEY: signingKey },
            })
        ).rejects.toBeInstanceOf(IdTokenReissueError)
    })

    it('keeps the regional audience when the request named no client', async () => {
        // A request can authenticate without naming a client in the body, through a client
        // assertion or the Authorization header, leaving the regional audience as the only one.
        const idToken = await signRegionalIdToken(regionalKey)

        const reissued = await reissueIdToken(idToken, {
            region: 'us',
            issuer: 'https://oauth.flind.example',
            audience: null,
            permittedUpstreamAudiences: [],
            env: { ...ownedFlindRegions, OIDC_SIGNING_KEY: signingKey },
        })

        expect(decodeJwt(reissued).aud).toBe(REGIONAL_CLIENT_ID)
    })

    it('still publishes the proxy keys when neither region answers', async () => {
        // A relying party verifying an ID token this worker issued needs no regional key, so an
        // outage of both regions must not take proxy-issued tokens down with it.
        vi.stubGlobal(
            'fetch',
            vi.fn(() => Promise.resolve(new Response('nope', { status: 500 })))
        )

        vi.resetModules()
        const { handleJwks: freshHandleJwks } = await import('@/handlers/passthrough')

        const response = await freshHandleJwks(
            new Request('https://oauth.flind.example/.well-known/jwks.json'),
            createMockKV(),
            {
                OIDC_SIGNING_KEY: signingKey,
                FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
                FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example',
            }
        )
        const { keys } = (await response.json()) as { keys: JWK[] }

        expect(response.status).toBe(200)
        expect(response.headers.get('cache-control')).toBe('no-store')
        expect(keys).toHaveLength(1)
    })

    it('does not cache a JWKS document that is missing a region', async () => {
        // Caching a partial document leaves tokens from the failed region unverifiable for the
        // whole TTL, long after it recovers.
        vi.stubGlobal(
            'fetch',
            vi.fn((url: string) =>
                Promise.resolve(
                    url.includes('eu.flind.example')
                        ? new Response('nope', { status: 500 })
                        : new Response(JSON.stringify({ keys: [regionalKey.publicJwk] }), { status: 200 })
                )
            )
        )

        // A fresh module instance, because the JWKS cache is module state an earlier test fills.
        vi.resetModules()
        const { handleJwks: freshHandleJwks } = await import('@/handlers/passthrough')

        const response = await freshHandleJwks(
            new Request('https://oauth.flind.example/.well-known/jwks.json'),
            createMockKV(),
            {
                OIDC_SIGNING_KEY: signingKey,
                FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
                FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example',
            }
        )

        expect(response.status).toBe(200)
        expect(response.headers.get('cache-control')).toBe('no-store')
    })
})
