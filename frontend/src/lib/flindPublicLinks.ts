/** Optional public Flind pages. Missing or unowned links must never open a different provider. */
export type FlindPublicPage = 'docs' | 'changelog' | 'community' | 'roadmap' | 'terms' | 'privacy'

type LinkConfig = Partial<Record<FlindPublicPage, string | undefined>>

const ownedHostname: string = import.meta.env.VITE_FLIND_WEBSITE_HOST || ''
const configuredLinks: LinkConfig = {
    docs: import.meta.env.VITE_FLIND_DOCS_URL,
    changelog: import.meta.env.VITE_FLIND_CHANGELOG_URL,
    community: import.meta.env.VITE_FLIND_COMMUNITY_URL,
    roadmap: import.meta.env.VITE_FLIND_ROADMAP_URL,
    terms: import.meta.env.VITE_FLIND_TERMS_URL,
    privacy: import.meta.env.VITE_FLIND_PRIVACY_URL,
}

export function flindPublicUrl(
    page: FlindPublicPage,
    hostname: string = ownedHostname,
    links: LinkConfig = configuredLinks
): string | null {
    if (
        !hostname ||
        hostname.length > 253 ||
        !/^[a-z0-9][a-z0-9.-]*[a-z0-9]$/.test(hostname) ||
        hostname.includes('..') ||
        hostname.split('.').some((part) => part.length > 63 || part.startsWith('-') || part.endsWith('-'))
    ) {
        return null
    }
    const rawUrl = links[page]
    if (!rawUrl || typeof rawUrl !== 'string' || rawUrl !== rawUrl.trim()) {
        return null
    }
    try {
        const url = new URL(rawUrl)
        if (
            url.protocol !== 'https:' ||
            url.hostname !== hostname ||
            url.port ||
            url.username ||
            url.password ||
            url.hash
        ) {
            return null
        }
        return url.toString()
    } catch {
        return null
    }
}
