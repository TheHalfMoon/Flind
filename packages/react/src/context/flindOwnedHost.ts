import type { PostHogConfig } from 'posthog-js'

/**
 * The vendored Flind React provider is not allowed to use posthog-js's cloud
 * default. Only an operator-selected, non-donor HTTPS origin may be used.
 */
export function flindReactOwnedOrigin(value: unknown): string | null {
    if (typeof value !== 'string' || !value.trim()) {
        return null
    }
    try {
        const url = new URL(value.trim())
        const hostname = url.hostname.toLowerCase().replace(/\.+$/, '')
        const donor =
            hostname === 'posthog.com' ||
            hostname.endsWith('.posthog.com') ||
            hostname === 'posthog.dev' ||
            hostname.endsWith('.posthog.dev') ||
            hostname === 'posthogstatus.com' ||
            hostname.endsWith('.posthogstatus.com')
        const loopback = hostname === '127.0.0.1' || hostname === '[::1]'
        if (
            !hostname ||
            donor ||
            url.username ||
            url.password ||
            url.pathname !== '/' ||
            url.search ||
            url.hash ||
            (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback))
        ) {
            return null
        }
        return url.origin
    } catch {
        return null
    }
}

export function flindReactOwnedOptions(options?: Partial<PostHogConfig>): Partial<PostHogConfig> | null {
    const apiHost = flindReactOwnedOrigin(options?.api_host)
    if (!apiHost) {
        return null
    }
    const uiHost = options?.ui_host === undefined ? apiHost : flindReactOwnedOrigin(options.ui_host)
    if (!uiHost) {
        return null
    }
    return { ...options, api_host: apiHost, ui_host: uiHost }
}
