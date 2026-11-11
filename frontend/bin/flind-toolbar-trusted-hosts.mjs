/**
 * Customer-selected, exact-origin allowlist for browser pages permitted to message the
 * Flind extension. Empty by default: publishing an extension must not silently trust
 * inherited third-party hosts. Chrome match patterns cannot constrain ports.
 *
 * Example: FLIND_TOOLBAR_TRUSTED_ORIGINS=https://flind.example.org,https://team.example.org
 */
export function getTrustedFlindAppMatches(value = process.env.FLIND_TOOLBAR_TRUSTED_ORIGINS ?? '') {
    if (typeof value !== 'string') {
        throw new TypeError('FLIND_TOOLBAR_TRUSTED_ORIGINS must be a comma-separated string')
    }
    if (value.trim() === '') {
        return []
    }
    const matches = new Set()
    for (const candidate of value.split(',')) {
        const origin = candidate.trim()
        if (!origin) {
            throw new Error('FLIND_TOOLBAR_TRUSTED_ORIGINS contains an empty origin')
        }
        let url
        try {
            url = new URL(origin)
        } catch {
            throw new Error('FLIND_TOOLBAR_TRUSTED_ORIGINS must contain valid URL origins')
        }
        const isLocalDev = url.protocol === 'http:' && url.hostname === 'localhost'
        if (url.protocol !== 'https:' && !isLocalDev) {
            throw new Error('Flind toolbar origins must use HTTPS (except explicitly configured localhost)')
        }
        if (url.username || url.password || url.search || url.hash || url.pathname !== '/' || url.port) {
            throw new Error('Flind toolbar origins may not include credentials, paths, query, fragment or port')
        }
        if (origin !== url.origin && origin !== url.origin + '/') {
            throw new Error('Flind toolbar origins must be exact URLs without wildcards')
        }
        const hostname = url.hostname.toLowerCase()
        if (hostname === 'posthog.com' || hostname.endsWith('.posthog.com')) {
            throw new Error('Inherited PostHog hosts must not be trusted by Flind')
        }
        if (!/^[a-z0-9.-]+$/.test(hostname)) {
            throw new Error('Unsupported Flind toolbar hostname')
        }
        matches.add(url.origin + '/*')
    }
    return [...matches].sort()
}

/**
 * Return only a bounded opt-in manifest fragment. No inherited third-party
 * web origin can reach the extension when this fragment is absent.
 */
export function getFlindExternalConnectable(value = process.env.FLIND_TOOLBAR_TRUSTED_ORIGINS ?? '') {
    const matches = getTrustedFlindAppMatches(value)
    return matches.length ? { externally_connectable: { matches } } : {}
}
