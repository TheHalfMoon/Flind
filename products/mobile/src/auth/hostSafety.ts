/** Block inherited upstream identities from receiving Flind mobile credentials. */
export function isInheritedProviderHostname(hostname: string): boolean {
    const value = hostname.trim().toLowerCase().replace(/\.$/, '')
    return value === 'posthog.com' || value.endsWith('.posthog.com') ||
        value === 'posthog.dev' || value.endsWith('.posthog.dev')
}
