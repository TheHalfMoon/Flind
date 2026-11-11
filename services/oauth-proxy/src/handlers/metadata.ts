import { proxyOrigin } from '@/lib/constants'
import { type FlindOAuthRegionEnv, flindOAuthDiscoveryOrigin } from '@/lib/flind-oauth-admission'

/**
 * Discovery documents are fetched only from the operator-configured Flind US
 * OAuth backend, and public endpoints are rewritten onto this proxy.
 */

const CACHE_TTL_MS = 600 * 1000

const MANIFEST_PATH = '/auth.md'

// The Flind regional server URL is identity metadata, not a proxy endpoint.
// Preserve it when translating upstream extensions into Flind-owned names.
const REGION_VALUE_FIELD = 'flind_base_url'
const REGIONAL_METADATA_ALIASES: Readonly<Record<string, string>> = {
    posthog_region: 'flind_region',
    posthog_base_url: REGION_VALUE_FIELD,
}

type Metadata = Record<string, unknown>

interface CachedDocument {
    body: string
    cachedUntil: number
}

const cache = new Map<string, CachedDocument>()

async function fetchAuthoritativeMetadata(path: string, regionalOrigin: string): Promise<Metadata> {
    const response = await fetch(`${regionalOrigin}${path}`)
    if (!response.ok) {
        throw new Error(`Failed to fetch ${path}: ${response.statusText}`)
    }

    return response.json() as Promise<Metadata>
}

/**
 * Walk a document and rewrite regional URL paths to this Flind proxy, including
 * nested endpoint fields such as `agent_auth.skill`.
 *
 * Matching on the URL rather than on a list of field names means an endpoint added to
 * the regional OAuth backend is rewritten here without a matching change.
 */
function rewriteEndpoints(value: unknown, origin: string, regionalOrigin: string): unknown {
    if (typeof value === 'string') {
        // Match an entire origin boundary, not a deceptive lookalike hostname.
        return value === regionalOrigin || value.startsWith(`${regionalOrigin}/`)
            ? `${origin}${value.slice(regionalOrigin.length)}`
            : value
    }

    if (Array.isArray(value)) {
        return value.map((item) => rewriteEndpoints(item, origin, regionalOrigin))
    }

    if (value && typeof value === 'object') {
        const data = value as Metadata
        // Backend compatibility is input-only: discovery clients see Flind
        // extension names. Native Flind fields take precedence over aliases.
        return Object.fromEntries(
            Object.entries(data).flatMap(([field, nested]) => {
                const publicField = REGIONAL_METADATA_ALIASES[field] ?? field
                if (publicField !== field && Object.prototype.hasOwnProperty.call(data, publicField)) {
                    return []
                }
                return [[
                    publicField,
                    publicField === REGION_VALUE_FIELD
                        ? nested
                        : rewriteEndpoints(nested, origin, regionalOrigin),
                ]]
            })
        )
    }

    return value
}

async function serveDocument(request: Request, path: string, env: FlindOAuthRegionEnv): Promise<Response> {
    const regionalOrigin = flindOAuthDiscoveryOrigin(env)
    if (!regionalOrigin) {
        return new Response('Flind OAuth discovery origin is not configured', {
            status: 503,
            headers: { 'Cache-Control': 'no-store' },
        })
    }
    const origin = proxyOrigin(request)
    // The backend origin belongs in the cache key to avoid cross-owner caching.
    const cacheKey = `${path}|${origin}|${regionalOrigin}`
    const cached = cache.get(cacheKey)

    if (!cached || cached.cachedUntil <= Date.now()) {
        try {
            const metadata = await fetchAuthoritativeMetadata(path, regionalOrigin)
            const body = JSON.stringify(rewriteEndpoints(metadata, origin, regionalOrigin))
            cache.set(cacheKey, { body, cachedUntil: Date.now() + CACHE_TTL_MS })
        } catch (error) {
            console.error(
                JSON.stringify({
                    handler: 'metadata',
                    path,
                    error: error instanceof Error ? error.message : 'unknown error',
                })
            )
            return new Response(
                JSON.stringify({
                    error: 'server_error',
                    error_description: 'Unable to fetch authorization server metadata',
                }),
                { status: 502, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } }
            )
        }
    }

    return new Response(cache.get(cacheKey)!.body, {
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=3600',
            'Access-Control-Allow-Origin': '*',
        },
    })
}

export async function handleMetadata(request: Request, _kv: KVNamespace, env: FlindOAuthRegionEnv): Promise<Response> {
    return serveDocument(request, '/.well-known/oauth-authorization-server', env)
}

export async function handleOpenIdConfiguration(request: Request, _kv: KVNamespace, env: FlindOAuthRegionEnv): Promise<Response> {
    return serveDocument(request, '/.well-known/openid-configuration', env)
}

/**
 * The grantable API scopes and what each one is for, built in posthog/api/oauth/scope_reference.py.
 * posthog.com reads it at build time, so a cached copy here keeps those builds off the app servers.
 */
export async function handleScopes(request: Request, _kv: KVNamespace, env: FlindOAuthRegionEnv): Promise<Response> {
    return serveDocument(request, '/oauth/scopes/', env)
}

/**
 * The auth.md agent manifest, which the authorization server metadata points at through
 * `agent_auth.skill`. Markdown rather than JSON, so the rewrite is a plain substitution: every URL
 * in the document is built from the serving instance's base URL.
 */
export async function handleClientManifest(request: Request, _kv: KVNamespace, env: FlindOAuthRegionEnv): Promise<Response> {
    const regionalOrigin = flindOAuthDiscoveryOrigin(env)
    if (!regionalOrigin) {
        return new Response('Flind OAuth discovery origin is not configured', {
            status: 503,
            headers: { 'Cache-Control': 'no-store' },
        })
    }
    const origin = proxyOrigin(request)
    const cacheKey = `${MANIFEST_PATH}|${origin}|${regionalOrigin}`
    const cached = cache.get(cacheKey)

    if (!cached || cached.cachedUntil <= Date.now()) {
        try {
            const response = await fetch(`${regionalOrigin}${MANIFEST_PATH}`)
            if (!response.ok) {
                throw new Error(`Failed to fetch ${MANIFEST_PATH}: ${response.statusText}`)
            }

            const body = (await response.text()).split(`${regionalOrigin}/`).join(`${origin}/`)
            cache.set(cacheKey, { body, cachedUntil: Date.now() + CACHE_TTL_MS })
        } catch (error) {
            console.error(
                JSON.stringify({
                    handler: 'manifest',
                    error: error instanceof Error ? error.message : 'unknown error',
                })
            )
            return new Response('Unable to fetch the client manifest', { status: 502 })
        }
    }

    return new Response(cache.get(cacheKey)!.body, {
        headers: {
            'Content-Type': 'text/markdown; charset=utf-8',
            'Cache-Control': 'public, max-age=3600',
            'Access-Control-Allow-Origin': '*',
        },
    })
}
