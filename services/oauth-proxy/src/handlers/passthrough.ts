import { type Region } from '@/lib/constants'
import { type FlindOAuthRegionEnv, type OAuthRegionalOrigins, flindOAuthOwnedRegionPair } from '@/lib/flind-oauth-admission'
import { type SigningKeyEnv, proxyJwks } from '@/lib/idtoken'
import { getClientMapping, getRegionSelection } from '@/lib/kv'
import { proxyPostWithClientId, proxyToRegionAtOrigins, tryBothRegionsAtOrigins } from '@/lib/proxy'
import { errorResponse } from '@/lib/validation'

/**
 * Passthrough handlers for OAuth endpoints that simply need to reach the correct region.
 */

// Every relying party fetches this on its first ID token verification. Signing keys rotate in months.
const JWKS_CACHE_TTL_MS = 600 * 1000

let cachedJwks: { body: string; cachedUntil: number; identity: string } | null = null

/**
 * Revoke token — route to the correct region based on client_id, fallback to try-both.
 */
export async function handleRevoke(
    request: Request, kv: KVNamespace, env: FlindOAuthRegionEnv
): Promise<Response> {
    const regions = flindOAuthOwnedRegionPair(env)
    if (!regions) {
        return new Response(JSON.stringify({ error: 'temporarily_unavailable' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
        })
    }
    return routeByClientId(request, kv, '/oauth/revoke/', regions)
}

/**
 * Introspect token — try US first, then EU.
 * Unlike tryBothRegions, we check the response body: introspect returns
 * 200 {"active": false} for unknown tokens, so HTTP status alone isn't enough.
 */
export async function handleIntrospect(
    request: Request, _kv: KVNamespace, env: FlindOAuthRegionEnv
): Promise<Response> {
    const regions = flindOAuthOwnedRegionPair(env)
    if (!regions) {
        return new Response(JSON.stringify({ error: 'temporarily_unavailable' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
        })
    }
    const body = await request.text()
    const headers = new Headers(request.headers)
    headers.delete('host')
    headers.delete('content-length')

    const usResponse = await fetch(new URL('/oauth/introspect/', regions.us).toString(), {
        method: 'POST',
        headers,
        body,
    })

    if (usResponse.ok) {
        const usData = await usResponse.json<Record<string, unknown>>()
        if (usData.active === true) {
            return new Response(JSON.stringify(usData), {
                status: 200,
                headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
            })
        }
    }

    const euHeaders = new Headers(request.headers)
    euHeaders.delete('host')
    euHeaders.delete('content-length')

    const euResponse = await fetch(new URL('/oauth/introspect/', regions.eu).toString(), {
        method: 'POST',
        headers: euHeaders,
        body,
    })

    return privateOAuthResponse(euResponse)
}

/**
 * UserInfo — try both regions with the Bearer token.
 */
export async function handleUserInfo(
    request: Request, _kv: KVNamespace, env: FlindOAuthRegionEnv
): Promise<Response> {
    const regions = flindOAuthOwnedRegionPair(env)
    if (!regions) {
        return new Response(JSON.stringify({ error: 'temporarily_unavailable' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
        })
    }
    const { response } = await tryBothRegionsAtOrigins(request, '/oauth/userinfo/', regions)
    return privateOAuthResponse(response)
}

/** Sensitive UserInfo and introspection results must never inherit a cacheable backend policy. */
function privateOAuthResponse(response: Response): Response {
    const headers = new Headers(response.headers)
    headers.set('Cache-Control', 'no-store')
    headers.delete('content-length')
    return new Response(response.body, { status: response.status, statusText: response.statusText, headers })
}

/**
 * JWKS — this proxy's signing keys, plus the regional ones.
 *
 * The regional keys stay published because the regional servers also sign the ID-JAG access
 * tokens (`at+jwt`) clients receive through this proxy. Key ids differ, so a verifier selects
 * the right key on its own.
 */
export async function handleJwks(
    request: Request, _kv: KVNamespace, env: SigningKeyEnv & FlindOAuthRegionEnv
): Promise<Response> {
    const regions = flindOAuthOwnedRegionPair(env)
    if (!regions) {
        return new Response(JSON.stringify({ error: 'temporarily_unavailable' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
        })
    }
    // Never reuse a cached JWKS after a signing-key rotation or a change of
    // owner-controlled regional authority. Only public key IDs enter the
    // identity; PEM signing material never enters the cache identity string.
    const proxyKeys = await proxyJwks(env)
    const identity = JSON.stringify({ us: regions.us, eu: regions.eu, kids: proxyKeys.map((key) => key.kid) })
    const cached = cachedJwks && cachedJwks.identity === identity && cachedJwks.cachedUntil > Date.now()
        ? cachedJwks.body : null
    if (cached) {
        return jwksResponse(cached)
    }

    const regional = await Promise.all([
        regionalKeys(request, 'us', regions),
        regionalKeys(request, 'eu', regions),
    ])

    // A relying party verifying an ID token this worker issued needs no regional key, so failing
    // the whole document would break that verification for as long as both regions are down.
    if (proxyKeys.length === 0 && regional.every((keys) => keys.length === 0)) {
        return new Response(JSON.stringify({ error: 'server_error' }), {
            status: 502,
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
        })
    }

    const body = JSON.stringify({ keys: dedupeByKid([...proxyKeys, ...regional.flat()]) })

    // A document missing a region's keys leaves tokens from that region unverifiable, so it is
    // served once but never held: the next request retries the region that failed.
    const complete = regional.every((keys) => keys.length > 0)
    if (complete) {
        cachedJwks = { body, cachedUntil: Date.now() + JWKS_CACHE_TTL_MS, identity }
    }

    return jwksResponse(body, complete)
}

/** A region that is unreachable contributes nothing rather than failing the whole document. */
async function regionalKeys(request: Request, region: Region, origins: OAuthRegionalOrigins): Promise<unknown[]> {
    try {
        const response = await proxyToRegionAtOrigins(request, region, '/.well-known/jwks.json', origins)
        if (response.ok) {
            const body = (await response.json()) as { keys?: unknown }
            // A non-array `keys` passes the emptiness check in `handleJwks` on its own length,
            // which would publish and cache it as a key.
            return Array.isArray(body.keys) ? body.keys : []
        }
        console.error(JSON.stringify({ handler: 'jwks', region, status: response.status }))
    } catch {
        console.error(JSON.stringify({ handler: 'jwks', region, error: 'unreachable' }))
    }

    return []
}

function dedupeByKid(keys: unknown[]): unknown[] {
    const seen = new Set<string>()
    return keys.filter((key) => {
        const kid = (key as { kid?: string }).kid
        if (!kid || seen.has(kid)) {
            return !kid
        }
        seen.add(kid)
        return true
    })
}

function jwksResponse(body: string, complete = true): Response {
    return new Response(body, {
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': complete ? `public, max-age=${JWKS_CACHE_TTL_MS / 1000}` : 'no-store',
            'Access-Control-Allow-Origin': '*',
        },
    })
}

async function routeByClientId(
    request: Request, kv: KVNamespace, path: string, regions: OAuthRegionalOrigins
): Promise<Response> {
    const body = await request.text()

    const contentType = request.headers.get('content-type') || ''
    let clientId: string | null = null

    if (contentType.includes('application/json')) {
        try {
            const json = JSON.parse(body) as Record<string, unknown>
            clientId = (json.client_id as string) || null
        } catch {
            return errorResponse({ error: 'invalid_request', error_description: 'Malformed JSON body' })
        }
    } else {
        const params = new URLSearchParams(body)
        clientId = params.get('client_id')
    }

    const rebuild = (): Request =>
        new Request(request.url, {
            method: request.method,
            headers: request.headers,
            body,
        })

    if (clientId) {
        const region = await getRegionSelection(kv, clientId)
        if (region) {
            const mapping = await getClientMapping(kv, clientId)
            if (mapping) {
                const regionalClientId = region === 'eu' ? mapping.eu_client_id : mapping.us_client_id
                if (regionalClientId) {
                    return proxyPostWithClientId(rebuild(), region, path, clientId, regionalClientId, undefined, undefined, regions)
                }
            }
        }
    }

    const { response } = await tryBothRegionsAtOrigins(rebuild(), path, regions)
    return response
}
