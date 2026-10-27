import { decodeJwt } from 'jose'

import { type Region } from './constants'
import { type FlindOAuthRegionEnv, type OAuthRegionalOrigins, flindOAuthOwnedRegionPair } from './flind-oauth-admission'
import { IdTokenReissueError, type SigningKeyEnv, reissueIdToken } from './idtoken'

/** Replace the regional ID token in a token response with one this proxy issued. */
export async function reissueIdTokenInResponse(
    response: Response,
    options: { issuer: string; audience: string | null; permittedUpstreamAudiences: string[]; env: SigningKeyEnv & FlindOAuthRegionEnv }
): Promise<Response> {
    if (!response.ok) {
        return response
    }

    const raw = await response.text()
    let payload: Record<string, unknown>
    try {
        payload = JSON.parse(raw) as Record<string, unknown>
    } catch {
        return rebuildResponse(response, raw)
    }

    const idToken = payload.id_token
    if (typeof idToken !== 'string') {
        return rebuildResponse(response, raw)
    }

    // Never leak an unverified regional identity assertion when signing is unavailable.
    if (!options.env.OIDC_SIGNING_KEY) {
        return serverError('OIDC signing key is not configured')
    }
    const regions = flindOAuthOwnedRegionPair(options.env)
    if (!regions) {
        return serverError('Flind regional issuer trust is not configured')
    }
    const region = regionOfIssuer(idToken, regions)
    if (!region) {
        return serverError('Could not determine which region issued the ID token')
    }

    try {
        const reissued = await reissueIdToken(idToken, {
            region,
            issuer: options.issuer,
            audience: options.audience,
            permittedUpstreamAudiences: options.permittedUpstreamAudiences,
            env: options.env,
        })
        return rebuildResponse(response, JSON.stringify({ ...payload, id_token: reissued }))
    } catch (error) {
        // Serving the regional token instead would quietly restore the issuer mismatch.
        console.error(
            JSON.stringify({
                handler: 'token',
                id_token: 'reissue_failed',
                region,
                error: error instanceof IdTokenReissueError ? error.message : (error as Error)?.constructor?.name,
            })
        )
        return serverError('Unable to issue an ID token')
    }
}

/** The unverified claim only selects a key set; the signature is still verified against it. */
function regionOfIssuer(idToken: string, regions: OAuthRegionalOrigins): Region | null {
    try {
        // This unverified value only selects the allowlisted key authority;
        // reissueIdToken validates both the signature and exact issuer.
        const issuer = decodeJwt(idToken).iss
        return issuer === regions.us ? 'us' : issuer === regions.eu ? 'eu' : null
    } catch {
        return null
    }
}

function rebuildResponse(response: Response, body: string): Response {
    const headers = new Headers(response.headers)
    // The body was re-serialized, so any upstream length no longer describes it.
    headers.delete('content-length')

    return new Response(body, { status: response.status, statusText: response.statusText, headers })
}

function serverError(description: string): Response {
    return new Response(JSON.stringify({ error: 'server_error', error_description: description }), {
        status: 500,
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
    })
}
