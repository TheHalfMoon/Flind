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

/**
 * Owned US origin for isolated discovery/manifest source qualification.
 * The Worker ingress gate STILL refuses public discovery until all regional
 * OAuth routes are migrated together. Direct handler invocation must never
 * fetch from inherited hosts, even when its entry router is bypassed in tests.
 */
export function flindOAuthDiscoveryOrigin(env: FlindOAuthRegionEnv): string | null {
    return safeOwnedOrigin(env.FLIND_OAUTH_US_ORIGIN)
}

export function flindOAuthOwnedRegionPair(env: FlindOAuthRegionEnv): OAuthRegionalOrigins | null {
    const us = safeOwnedOrigin(env.FLIND_OAUTH_US_ORIGIN)
    const eu = safeOwnedOrigin(env.FLIND_OAUTH_EU_ORIGIN)
    if (!us || !eu || us === eu) {
        return null
    }
    return { us, eu }
}

export function flindOAuthRuntimeReady(
    env: FlindOAuthRegionEnv,
    actualHandlerOrigins: OAuthRegionalOrigins
): boolean {
    const approved = flindOAuthOwnedRegionPair(env)
    if (!approved) {
        return false
    }

    // Operator intent alone cannot enable the legacy handler code.
    // Full worker ingress stays unavailable until every active route uses
    // these exact first-party backends, including token/JWKS/issuer paths.
    return actualHandlerOrigins.us === approved.us && actualHandlerOrigins.eu === approved.eu
}
