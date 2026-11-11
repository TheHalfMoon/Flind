// Token store + refresh for the standalone OAuth frontend. Plain TS (no kea) so that
// `api.ts` and other non-React callers can read a valid bearer token directly.
// `oauthLogic` wraps this for the login UI.

import { flindRegionHost } from 'lib/flindRegionHosts'

import { OrganizationType, Region, TeamType, UserType } from '~/types'

import { generateCodeChallenge } from './pkce'
import { flindBuildEnv } from 'lib/flindBuildEnv'

export interface OAuthRegionConfig {
    key: Region.US | Region.EU
    label: string
    flag: string
    host: string
    clientId: string
}

// Flind never inherits cloud endpoints or OAuth client IDs. Both the region
// hostname and the client ID require operator configuration and registration.
const flindOAuthHost = (region: Region.US | Region.EU): string => {
    const host = flindRegionHost(region)
    return host ? `https://${host}` : ''
}

export const OAUTH_REGIONS: Record<Region.US | Region.EU, OAuthRegionConfig> = {
    [Region.US]: {
        key: Region.US,
        label: 'Flind US',
        flag: '🇺🇸',
        host: flindOAuthHost(Region.US),
        clientId: flindBuildEnv.VITE_FLIND_OAUTH_US_CLIENT_ID || '',
    },
    [Region.EU]: {
        key: Region.EU,
        label: 'Flind EU',
        flag: '🇪🇺',
        host: flindOAuthHost(Region.EU),
        clientId: flindBuildEnv.VITE_FLIND_OAUTH_EU_CLIENT_ID || '',
    },
}

export function configuredOAuthRegion(region: Region.US | Region.EU): OAuthRegionConfig | null {
    const config = OAUTH_REGIONS[region]
    if (!config?.host || !config.clientId || !/^[A-Za-z0-9._~-]{3,128}$/.test(config.clientId)) {
        return null
    }
    try {
        const parsed = new URL(config.host)
        // A custom TLS port is never an approved first-party OAuth issuer.
        // URL.origin includes the port, so comparing origin alone would let
        // https://host:8443 pass when the stored config contained that port.
        if (
            parsed.protocol !== 'https:' ||
            parsed.port ||
            parsed.origin !== config.host ||
            parsed.username ||
            parsed.password
        ) {
            return null
        }
        return config
    } catch {
        return null
    }
}

export function isApprovedOAuthTarget(backendHost: string, clientId: string): boolean {
    return ([Region.US, Region.EU] as const).some((region) => {
        const config = configuredOAuthRegion(region)
        return !!config && backendHost === config.host && clientId === config.clientId
    })
}

/** The Flind OAuth region with a currently configured, exact backend host. */
export function getRegionForHost(host: string): Region.US | Region.EU | null {
    for (const region of [Region.US, Region.EU] as const) {
        if (configuredOAuthRegion(region)?.host === host) {
            return region
        }
    }
    return null
}

/** Where the OAuth provider redirects back to — this frontend's own origin (e.g. http://localhost:8010). */
function getRedirectUri(): string {
    return `${window.location.origin}/oauth/callback`
}

const SESSION_KEY = 'flind_oauth_session'
// Tokenless dev marker so the DEBUG-gated backend serves the SPA in OAuth mode (value = region).
// NOT a secure cookie (client-set, forgeable, no httpOnly/Secure) — never gate production auth on
// it. The backend only honors it under DEBUG (see login_required in posthog/views.py).
const OAUTH_MODE_COOKIE = 'flind_oauth_mode'

export interface OAuthSession {
    backendHost: string
    clientId: string
    accessToken: string
    refreshToken: string
    /** Epoch ms when the access token expires. */
    expiresAt: number
}

export interface PendingAuth {
    backendHost: string
    clientId: string
    codeVerifier: string
    state: string
    /** In-app path to return to once the flow completes. */
    returnTo: string
}

interface TokenResponse {
    access_token: string
    refresh_token: string
    expires_in: number
}

/**
 * OAuth mode is active when a cloud OAuth session is stored: the frontend then talks to the
 * remote region with a bearer token instead of the local backend's session cookie.
 */
export function isOAuthMode(): boolean {
    return !!getStoredSession()
}

export function getStoredSession(): OAuthSession | null {
    try {
        const raw = window.localStorage.getItem(SESSION_KEY)
        if (!raw) {
            return null
        }
        const session: unknown = JSON.parse(raw)
        if (!session || typeof session !== 'object') {
            return null
        }
        const data = session as Partial<OAuthSession>
        if (
            typeof data.backendHost !== 'string' ||
            typeof data.clientId !== 'string' ||
            !isApprovedOAuthTarget(data.backendHost, data.clientId) ||
            typeof data.accessToken !== 'string' ||
            !data.accessToken ||
            typeof data.refreshToken !== 'string' ||
            !data.refreshToken ||
            typeof data.expiresAt !== 'number' ||
            !Number.isFinite(data.expiresAt)
        ) {
            return null
        }
        return data as OAuthSession
    } catch {
        return null
    }
}

export function getBackendHost(): string | null {
    return getStoredSession()?.backendHost ?? null
}

function storeSession(session: OAuthSession): void {
    if (!isApprovedOAuthTarget(session.backendHost, session.clientId)) {
        throw new Error('Flind OAuth backend is not configured for this instance.')
    }
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
    // Persistent (400d cap) to track the localStorage session across browser restarts.
    document.cookie = `${OAUTH_MODE_COOKIE}=${getRegionForHost(session.backendHost) ?? '1'}; path=/; Max-Age=34560000; SameSite=Lax`
}

export function clearSession(): void {
    window.localStorage.removeItem(SESSION_KEY)
    // Clean a legacy session without ever trusting it as a Flind OAuth source.
    window.localStorage.removeItem('ph_oauth_session')
    document.cookie = `${OAUTH_MODE_COOKIE}=; path=/; Max-Age=0; SameSite=Lax`
    document.cookie = 'ph_oauth_mode=; path=/; Max-Age=0; SameSite=Lax'
    // Drop the bootstrap ids with the session so a later login in the same tab can't read the
    // previous account's ids before its own /api/users/@me/ resolves.
    oauthContextIds = null
}

export interface OAuthContextIds {
    teamId?: TeamType['id']
    organizationId?: OrganizationType['id']
    userId?: UserType['uuid']
}

// In OAuth mode getAppContext() has no server-rendered context, so these bootstrap ids are pushed
// here from userLogic once the remote user loads, and read back by getAppContext's synchronous
// getters. Lives alongside the session (not in getAppContext) so clearSession() can reset it, and
// so getAppContext stays a leaf module — importing the heavy lib/api there caused a module-init cycle.
let oauthContextIds: OAuthContextIds | null = null

export function setOAuthContextIds(ids: OAuthContextIds | null): void {
    oauthContextIds = ids
}

export function getOAuthContextIds(): OAuthContextIds | null {
    return oauthContextIds
}

function sessionFromTokenResponse(backendHost: string, clientId: string, data: TokenResponse): OAuthSession {
    return {
        backendHost,
        clientId,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        expiresAt: Date.now() + data.expires_in * 1000,
    }
}

/** Full authorize URL for a flow; also computes the S256 challenge from the stored verifier. */
export async function buildAuthorizeUrl(pending: PendingAuth): Promise<string> {
    if (!isApprovedOAuthTarget(pending.backendHost, pending.clientId)) {
        throw new Error('Flind OAuth is not configured for this region.')
    }
    const codeChallenge = await generateCodeChallenge(pending.codeVerifier)
    const url = new URL(`${pending.backendHost}/oauth/authorize`)
    url.searchParams.set('client_id', pending.clientId)
    url.searchParams.set('redirect_uri', getRedirectUri())
    url.searchParams.set('response_type', 'code')
    url.searchParams.set('code_challenge', codeChallenge)
    url.searchParams.set('code_challenge_method', 'S256')
    url.searchParams.set('scope', '*') // All scopes, just like the desktop app
    url.searchParams.set('state', pending.state)
    return url.toString()
}

/** Exchange the authorization code for tokens and persist the session. */
export async function exchangeCodeForToken(pending: PendingAuth, code: string, state: string): Promise<OAuthSession> {
    if (!isApprovedOAuthTarget(pending.backendHost, pending.clientId)) {
        throw new Error('Flind OAuth is not configured for this region.')
    }
    if (pending.state !== state) {
        throw new Error('OAuth state mismatch. Please start the login again.')
    }
    // Trailing slash is required: CORS_URLS_REGEX only grants CORS headers to `/oauth/token/`.
    const response = await fetch(`${pending.backendHost}/oauth/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            grant_type: 'authorization_code',
            code,
            redirect_uri: getRedirectUri(),
            client_id: pending.clientId,
            code_verifier: pending.codeVerifier,
        }),
    })
    if (!response.ok) {
        throw new Error(`Token exchange failed: ${response.status} ${await response.text()}`)
    }
    const session = sessionFromTokenResponse(
        pending.backendHost,
        pending.clientId,
        (await response.json()) as TokenResponse
    )
    storeSession(session)
    return session
}

// Dedupe concurrent refreshes so a burst of 401s triggers a single token request.
let refreshPromise: Promise<string | null> | null = null

export function refreshAccessToken(): Promise<string | null> {
    if (!refreshPromise) {
        refreshPromise = doRefresh().finally(() => {
            refreshPromise = null
        })
    }
    return refreshPromise
}

async function doRefresh(): Promise<string | null> {
    const session = getStoredSession()
    if (!session) {
        return null
    }
    let response: Response
    try {
        response = await fetch(`${session.backendHost}/oauth/token/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                grant_type: 'refresh_token',
                refresh_token: session.refreshToken,
                client_id: session.clientId,
            }),
        })
    } catch {
        // Network error — keep the session so a later request can retry.
        return null
    }
    if (!response.ok) {
        // A rejected refresh token is terminal: clear the session and force re-login.
        if (response.status === 400 || response.status === 401) {
            clearSession()
        }
        return null
    }
    const updated = sessionFromTokenResponse(
        session.backendHost,
        session.clientId,
        (await response.json()) as TokenResponse
    )
    storeSession(updated)
    return updated.accessToken
}
