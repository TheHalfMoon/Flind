import { type Region } from './constants'
import { type OAuthRegionalOrigins, flindOAuthOwnedRegionPair } from './flind-oauth-admission'

/** Never send credentials to an absent or inherited region, even in direct helper calls. */
function checkedOrigins(origins: OAuthRegionalOrigins | undefined): OAuthRegionalOrigins | null {
    return flindOAuthOwnedRegionPair({
        FLIND_OAUTH_US_ORIGIN: origins?.us,
        FLIND_OAUTH_EU_ORIGIN: origins?.eu,
    })
}

function blockedEgress(): Response {
    return new Response(JSON.stringify({ error: 'temporarily_unavailable' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
    })
}

export async function proxyToRegionAtOrigins(
    request: Request, region: Region, path: string, ownedOrigins: OAuthRegionalOrigins
): Promise<Response> {
    const regions = checkedOrigins(ownedOrigins)
    if (!regions) {
        return blockedEgress()
    }
    const url = new URL(path, regions[region])

    const headers = new Headers(request.headers)
    headers.delete('host')

    return fetch(url.toString(), {
        method: request.method,
        headers,
        body: request.body,
    })
}

/**
 * Proxy a form-encoded or JSON POST body to a region, optionally rewriting the client_id.
 */
export async function proxyPostWithClientId(
    request: Request,
    region: Region,
    path: string,
    proxyClientId: string,
    regionalClientId: string,
    redirectUriRewrite?: { from: string; to: string },
    clientSecretRewrite?: { from: string; to: string },
    ownedOrigins?: OAuthRegionalOrigins
): Promise<Response> {
    const regions = checkedOrigins(ownedOrigins)
    if (!regions) {
        return blockedEgress()
    }
    const contentType = request.headers.get('content-type') || ''
    let body: string

    if (contentType.includes('application/json')) {
        const json = await request.json<Record<string, unknown>>()
        if (json.client_id === proxyClientId) {
            json.client_id = regionalClientId
        }
        if (redirectUriRewrite && json.redirect_uri === redirectUriRewrite.from) {
            json.redirect_uri = redirectUriRewrite.to
        }
        if (clientSecretRewrite && json.client_secret === clientSecretRewrite.from) {
            json.client_secret = clientSecretRewrite.to
        }
        body = JSON.stringify(json)
    } else {
        // form-urlencoded
        const text = await request.text()
        const params = new URLSearchParams(text)
        if (params.get('client_id') === proxyClientId) {
            params.set('client_id', regionalClientId)
        }
        if (redirectUriRewrite && params.get('redirect_uri') === redirectUriRewrite.from) {
            params.set('redirect_uri', redirectUriRewrite.to)
        }
        if (clientSecretRewrite && params.get('client_secret') === clientSecretRewrite.from) {
            params.set('client_secret', clientSecretRewrite.to)
        }
        body = params.toString()
    }

    const url = new URL(path, regions[region])

    const headers = new Headers(request.headers)
    headers.delete('host')
    // Body was rewritten so the original content-length is wrong
    headers.delete('content-length')

    return fetch(url.toString(), {
        method: 'POST',
        headers,
        body,
    })
}

/** A POST may use US then EU only after verifying both explicitly owned destinations. */
/** Proxy a POST to two validated, explicitly supplied Flind regional origins. */
export async function tryBothRegionsAtOrigins(
    request: Request,
    path: string,
    origins: OAuthRegionalOrigins
): Promise<{ response: Response; region: Region | null }> {
    const checked = checkedOrigins(origins)
    if (!checked) {
        return { response: blockedEgress(), region: null }
    }
    const body = await request.text()
    const headers = new Headers(request.headers)
    headers.delete('host')

    const usUrl = new URL(path, checked.us)
    const usResponse = await fetch(usUrl.toString(), {
        method: 'POST',
        headers,
        body,
    })

    if (usResponse.ok) {
        console.info(JSON.stringify({ fn: 'tryBothRegions', path, resolved: 'us', us_status: usResponse.status }))
        return { response: usResponse, region: 'us' }
    }

    const euHeaders = new Headers(request.headers)
    euHeaders.delete('host')
    const euUrl = new URL(path, checked.eu)
    const euResponse = await fetch(euUrl.toString(), {
        method: 'POST',
        headers: euHeaders,
        body,
    })

    if (euResponse.ok) {
        console.info(
            JSON.stringify({
                fn: 'tryBothRegions',
                path,
                resolved: 'eu',
                us_status: usResponse.status,
                eu_status: euResponse.status,
            })
        )
        return { response: euResponse, region: 'eu' }
    }

    const forwarded = preferClientError(usResponse, euResponse)
    console.error(
        JSON.stringify({
            fn: 'tryBothRegions',
            path,
            resolved: 'none',
            us_status: usResponse.status,
            eu_status: euResponse.status,
            forwarded_from: forwarded === usResponse ? 'us' : 'eu',
        })
    )
    return { response: forwarded, region: null }
}

/**
 * Pick which of two rejections to forward to the client.
 *
 * A 4xx carries the OAuth error code the client acts on: `invalid_grant` tells it
 * to discard the token and re-authorize. A 5xx only says one region was unhealthy,
 * which must not be reported as a dead grant.
 */
export function preferClientError(first: Response, second: Response): Response {
    if (isClientError(first)) {
        return first
    }
    return isClientError(second) ? second : first
}

function isClientError(response: Response): boolean {
    return response.status >= 400 && response.status < 500
}
