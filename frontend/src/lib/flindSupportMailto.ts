import { flindBuildEnv } from 'lib/flindBuildEnv'

/** Optional Flind-owned support mailbox. No inherited vendor fallback. */
export function flindSupportMailto(
    configuredEmail: string | undefined = flindBuildEnv.VITE_FLIND_SUPPORT_EMAIL,
    configuredDomain: string | undefined = flindBuildEnv.VITE_FLIND_SUPPORT_EMAIL_DOMAIN
): string | null {
    if (
        typeof configuredEmail !== 'string' ||
        typeof configuredDomain !== 'string' ||
        !configuredEmail ||
        !configuredDomain ||
        configuredEmail.length > 254 ||
        configuredEmail !== configuredEmail.trim() ||
        configuredDomain !== configuredDomain.trim()
    ) {
        return null
    }

    const domain = configuredDomain.toLowerCase()
    if (
        domain.length > 253 ||
        !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(domain) ||
        domain === 'posthog.com' ||
        domain.endsWith('.posthog.com')
    ) {
        return null
    }

    // Conservative one-mailbox validation; reject URL schemes, paths,
    // multiple recipients and query injection before composing a mailto.
    const match = /^([A-Za-z0-9._+-]{1,64})@([A-Za-z0-9.-]+)$/.exec(configuredEmail)
    if (!match || match[1].startsWith('.') || match[1].endsWith('.') || match[1].includes('..') || match[2].toLowerCase() !== domain) {
        return null
    }

    return `mailto:${configuredEmail}?subject=Flind%20support%20request`
}
