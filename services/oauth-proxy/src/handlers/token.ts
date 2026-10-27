import { type Region, proxyOrigin } from '@/lib/constants'
import { type SigningKeyEnv } from '@/lib/idtoken'
import { type FlindOAuthRegionEnv, type OAuthRegionalOrigins, flindOAuthOwnedRegionPair } from '@/lib/flind-oauth-admission'
import {
    getCallbackRedirectUri,
    getClientMapping,
    getRegionSelection,
    putRegionSelection,
    resolveMappingRewrite,
} from '@/lib/kv'
import { preferClientError, proxyPostWithClientId, proxyToRegionAtOrigins, tryBothRegionsAtOrigins } from '@/lib/proxy'
import { reissueIdTokenInResponse } from '@/lib/token-response'
import { duplicateParamError, errorResponse, findDuplicateParam } from '@/lib/validation'

/** RFC 7523, which Flind serves as the ID-JAG identity assertion exchange. */
const JWT_BEARER_GRANT_TYPE = 'urn:ietf:params:oauth:grant-type:jwt-bearer'

/**
 * RFC 6749 §5.1: token-bearing responses must not be stored by browsers,
 * shared proxies, or CDNs, regardless of the regional server's cache headers.
 * Apply this to both success and error responses without consuming their body.
 */
function privateTokenResponse(response: Response): Response {
    const headers = new Headers(response.headers)
    headers.set('Cache-Control', 'no-store')
    headers.set('Pragma', 'no-cache')
    headers.set('Expires', '0')
    for (const header of ['CDN-Cache-Control', 'Cloudflare-CDN-Cache-Control', 'Surrogate-Control', 'ETag', 'Last-Modified']) {
        headers.delete(header)
    }
    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
    })
}

// The proxy reads a form body with `.get()`, which returns the first value, while Django's
// QueryDict returns the last. A repeat lets the two authenticate different clients.
const SINGLE_VALUE_TOKEN_PARAMS = [
    'client_id',
    'client_secret',
    'grant_type',
    'code',
    'code_verifier',
    'refresh_token',
    'redirect_uri',
] as const

/**
 * OAuth Token Exchange — proxy to the correct region.
 *
 * Routes the token exchange to the correct regional Flind regional server.
 * Region is determined by KV lookup on client_id (stored during the authorize step).
 * For refresh_token grants, we fall back to try-both since the client may not
 * have gone through our authorize flow.
 */
export async function handleToken(
    request: Request, kv: KVNamespace, env: SigningKeyEnv & FlindOAuthRegionEnv
): Promise<Response> {
    const regions = flindOAuthOwnedRegionPair(env)
    if (!regions) {
        // Never read or forward grant credentials until regional Flind ownership
        // is configured. Direct handler calls get the same protection as Worker ingress.
        return privateTokenResponse(new Response(JSON.stringify({ error: 'temporarily_unavailable' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
        }))
    }
    const body = await request.text()

    const contentType = request.headers.get('content-type') || ''
    let clientId: string | null = null
    let grantType: string | null = null

    if (contentType.includes('application/json')) {
        try {
            const json = JSON.parse(body) as Record<string, unknown>
            clientId = (json.client_id as string) || null
            grantType = (json.grant_type as string) || null
        } catch {
            return privateTokenResponse(errorResponse(
                { error: 'invalid_request', error_description: 'Malformed JSON body' }
            ))
        }
    } else {
        const formParams = new URLSearchParams(body)
        const duplicate = findDuplicateParam(formParams, SINGLE_VALUE_TOKEN_PARAMS)
        if (duplicate) {
            return privateTokenResponse(errorResponse(duplicateParamError(duplicate)))
        }
        clientId = formParams.get('client_id')
        grantType = formParams.get('grant_type')
    }

    const response = await routeToken(request, kv, body, clientId, grantType, regions)

    if (grantType === JWT_BEARER_GRANT_TYPE) {
        // An ID-JAG exchange returns an access token and no ID token, so it has nothing to re-issue.
        return privateTokenResponse(response)
    }

    return privateTokenResponse(await reissueIdTokenInResponse(response, {
        issuer: proxyOrigin(request),
        audience: clientId,
        permittedUpstreamAudiences: response.ok && clientId ? await permittedUpstreamAudiences(kv, clientId) : [],
        env,
    }))
}

/** A client registered through the proxy is known to each region under its own id. */
async function permittedUpstreamAudiences(kv: KVNamespace, clientId: string): Promise<string[]> {
    const mapping = await getClientMapping(kv, clientId)
    if (!mapping) {
        return [clientId]
    }

    return [clientId, mapping.us_client_id, mapping.eu_client_id].filter((id) => Boolean(id))
}

async function routeToken(
    request: Request,
    kv: KVNamespace,
    body: string,
    clientId: string | null,
    grantType: string | null,
    regions: OAuthRegionalOrigins
): Promise<Response> {
    const clientIdPrefix = clientId?.slice(0, 8) ?? 'none'

    const rebuild = (): Request =>
        new Request(request.url, {
            method: request.method,
            headers: request.headers,
            body,
        })

    // The regional server checks the assertion's `client_id` claim against the posted one
    // (posthog/api/id_jag.py), so rewriting it to the regional id fails on EU. This grant needs
    // no rewrite: the assertion is the credential and no OAuth application is looked up.
    if (grantType === JWT_BEARER_GRANT_TYPE) {
        const { response, region } = await tryBothRegionsAtOrigins(rebuild(), '/oauth/token/', regions)
        console.info(
            JSON.stringify({
                handler: 'token',
                grant_type: grantType,
                client_id_prefix: clientIdPrefix,
                region_source: 'try_both_no_rewrite',
                resolved_region: region,
                status: response.status,
            })
        )
        return response
    }

    // Look up region by client_id (stored during the authorize step)
    if (clientId) {
        const region = await getRegionSelection(kv, clientId)
        if (region) {
            // If we intercepted the authorize callback, rewrite redirect_uri
            // so the regional server sees the proxy callback URL (which the auth code was issued for)
            const storedRedirectUri = await getCallbackRedirectUri(kv, clientId)
            let redirectUriRewrite: { from: string; to: string } | undefined
            if (storedRedirectUri) {
                const proxyCallbackUrl = `${new URL(request.url).origin}/oauth/callback/`
                redirectUriRewrite = { from: storedRedirectUri, to: proxyCallbackUrl }
            }

            console.info(
                JSON.stringify({
                    handler: 'token',
                    grant_type: grantType,
                    client_id_prefix: clientIdPrefix,
                    region_source: 'kv',
                    region,
                })
            )
            const response = await proxyWithMapping(rebuild(), kv, clientId, region, redirectUriRewrite, regions)
            console.info(
                JSON.stringify({
                    handler: 'token',
                    grant_type: grantType,
                    client_id_prefix: clientIdPrefix,
                    region_source: 'kv',
                    region,
                    status: response.status,
                })
            )
            return response
        }
    }

    // For refresh_token grants, try-both is safe (tokens are idempotent to verify).
    // For authorization_code grants without a stored region, return an error
    // rather than leaking the auth code to the wrong server.
    if (grantType === 'authorization_code') {
        console.info(
            JSON.stringify({
                handler: 'token',
                grant_type: grantType,
                client_id_prefix: clientIdPrefix,
                region_source: 'none',
                error: 'no_region_for_auth_code',
            })
        )
        return new Response(
            JSON.stringify({
                error: 'invalid_request',
                error_description: 'Unable to determine region for this authorization code',
            }),
            { status: 400, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } }
        )
    }

    // If the client was registered through the proxy, we have a permanent mapping
    // of proxy client_id → regional client_ids. Try each region with the correctly
    // rewritten client_id/secret so the regional server recognizes the client.
    // Without this, tryBothRegions sends the proxy (US) client_id to both regions,
    // and EU rejects it because it only knows its own EU client_id.
    if (clientId) {
        const mapping = await getClientMapping(kv, clientId)
        if (mapping) {
            let bestFailure: Response | null = null

            for (const candidateRegion of ['us', 'eu'] as Region[]) {
                const rewrite = resolveMappingRewrite(mapping, candidateRegion)
                if (!rewrite) {
                    continue
                }

                console.info(
                    JSON.stringify({
                        handler: 'token',
                        grant_type: grantType,
                        client_id_prefix: clientIdPrefix,
                        region_source: 'mapping_try_both',
                        candidate_region: candidateRegion,
                    })
                )

                const response = await proxyPostWithClientId(
                    rebuild(),
                    candidateRegion,
                    '/oauth/token/',
                    clientId,
                    rewrite.regionalClientId,
                    undefined,
                    rewrite.clientSecretRewrite,
                    regions
                )

                if (response.ok) {
                    // Re-store the region so subsequent refreshes take the fast path
                    await putRegionSelection(kv, clientId, candidateRegion)

                    console.info(
                        JSON.stringify({
                            handler: 'token',
                            grant_type: grantType,
                            client_id_prefix: clientIdPrefix,
                            region_source: 'mapping_try_both',
                            resolved_region: candidateRegion,
                            status: response.status,
                        })
                    )
                    return response
                }

                bestFailure = bestFailure ? preferClientError(bestFailure, response) : response
            }

            if (bestFailure) {
                console.error(
                    JSON.stringify({
                        handler: 'token',
                        grant_type: grantType,
                        client_id_prefix: clientIdPrefix,
                        region_source: 'mapping_try_both',
                        resolved_region: 'none',
                        status: bestFailure.status,
                    })
                )
                return bestFailure
            }

            console.error(
                JSON.stringify({
                    handler: 'token',
                    grant_type: grantType,
                    client_id_prefix: clientIdPrefix,
                    region_source: 'mapping_try_both',
                    resolved_region: 'none',
                    error: 'no_region_candidates',
                })
            )
            return new Response(
                JSON.stringify({
                    error: 'invalid_request',
                    error_description: 'Unable to determine region',
                }),
                { status: 400, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } }
            )
        }
    }

    // No mapping — client may have registered directly with a regional server.
    // Try both regions with the raw request.
    console.info(
        JSON.stringify({
            handler: 'token',
            grant_type: grantType,
            client_id_prefix: clientIdPrefix,
            region_source: 'try_both',
        })
    )
    const { response, region } = await tryBothRegionsAtOrigins(rebuild(), '/oauth/token/', regions)
    const summary = JSON.stringify({
        handler: 'token',
        grant_type: grantType,
        client_id_prefix: clientIdPrefix,
        region_source: 'try_both',
        resolved_region: region,
        status: response.status,
    })
    if (region) {
        console.info(summary)
    } else {
        console.error(summary)
    }
    return response
}

async function proxyWithMapping(
    request: Request,
    kv: KVNamespace,
    proxyClientId: string | null,
    region: Region,
    redirectUriRewrite: { from: string; to: string } | undefined,
    regions: OAuthRegionalOrigins
): Promise<Response> {
    if (proxyClientId) {
        const mapping = await getClientMapping(kv, proxyClientId)
        if (mapping) {
            const rewrite = resolveMappingRewrite(mapping, region)
            if (rewrite) {
                return proxyPostWithClientId(
                    request,
                    region,
                    '/oauth/token/',
                    proxyClientId,
                    rewrite.regionalClientId,
                    redirectUriRewrite,
                    rewrite.clientSecretRewrite,
                    regions
                )
            }
        }
    }

    // A code was issued for the selected region; never retry that code at
    // the other region when the client mapping was missing from KV.
    return proxyToRegionAtOrigins(request, region, '/oauth/token/', regions)
}
