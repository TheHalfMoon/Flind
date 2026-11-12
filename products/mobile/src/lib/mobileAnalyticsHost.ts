/**
 * Mobile telemetry is OFF without an explicitly configured Flind-controlled
 * HTTPS collector. Never fall back to third-party SDK infrastructure.
 */
export function ownedAnalyticsHost(value: string | undefined): string | null {
    if (!value?.trim()) return null
    try {
        const parsed = new URL(value.trim())
        const hostname = parsed.hostname.toLowerCase().replace(/\.$/, '')
        if (
            parsed.protocol !== 'https:' ||
            parsed.username ||
            parsed.password ||
            parsed.search ||
            parsed.hash ||
            (parsed.pathname !== '/' && parsed.pathname !== '') ||
            hostname === 'posthog.com' ||
            hostname.endsWith('.posthog.com') ||
            hostname === 'posthog.dev' ||
            hostname.endsWith('.posthog.dev')
        ) {
            return null
        }
        return parsed.origin
    } catch {
        return null
    }
}
