/**
 * Safe admission for Flind's not-yet-migrated regional OAuth proxy.
 *
 * Both first-party origins must be explicitly owned/configured, and the
 * *actual* handler destinations must match them. The current inherited
 * regional constants intentionally fail this gate until all downstream
 * OAuth/OIDC handlers have been migrated and qualified together.
 *
 * Do not replace the exact-runtime-matching check with a boolean feature
 * flag: doing so would re-enable customer token egress to old hosts.
 */
export interface FlindOAuthRegionEnv {
    FLIND_OAUTH_US_ORIGIN?: string
    FLIND_OAUTH_EU_ORIGIN?: string
}

export interface OAuthRegionalOrigins {
    us: string
    eu: string
}

const forbiddenOriginSuffixes = ['posthog.com', 'posthog.io']

function safeOwnedOrigin(value: unknown): string | null {
    if (typeof value !== 'string' || !value.trim() || value !== value.trim()) {
        return null
    }
    try {
        const parsed = new URL(value)
        const hostname = parsed.hostname.toLowerCase().replace(/\.$/, '')
        if (
            !hostname ||
            parsed.username ||
            parsed.password ||
            parsed.search ||
            parsed.hash ||
            (parsed.pathname !== '/' && parsed.pathname !== '') ||
            forbiddenOriginSuffixes.some(
                (suffix) =>
                    hostname === suffix ||
                    hostname.endsWith('.' + suffix) ||
                    hostname.startsWith(suffix + '.') ||
                    hostname.includes('.' + suffix + '.')
            )
        ) {
            return null
        }
        if (parsed.protocol !== 'https:' &&
            !(parsed.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(hostname))) {
            return null
        }
        return parsed.origin
    } catch {
        return null
    }
}

export function flindOAuthRuntimeReady(
    env: FlindOAuthRegionEnv,
    actualHandlerOrigins: OAuthRegionalOrigins
): boolean {
    const us = safeOwnedOrigin(env.FLIND_OAUTH_US_ORIGIN)
    const eu = safeOwnedOrigin(env.FLIND_OAUTH_EU_ORIGIN)
    if (!us || !eu || us === eu) {
        return false
    }

    // Critically: operator intent is not enough. The handlers themselves
    // must be routed to the same owner-approved origins. This currently
    // remains FALSE because legacy URL constants are not yet migrated.
    return actualHandlerOrigins.us === us && actualHandlerOrigins.eu === eu
}
