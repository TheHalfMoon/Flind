import { flindBuildEnv } from 'lib/flindBuildEnv'

/** Optional public Flind pages. Missing or unowned links must never open a different provider. */
export type FlindPublicPage = 'docs' | 'changelog' | 'community' | 'roadmap' | 'terms' | 'privacy'

type LinkConfig = Partial<Record<FlindPublicPage, string | undefined>>

const ownedHostname: string = flindBuildEnv.VITE_FLIND_WEBSITE_HOST || ''
const configuredLinks: LinkConfig = {
    docs: flindBuildEnv.VITE_FLIND_DOCS_URL,
    changelog: flindBuildEnv.VITE_FLIND_CHANGELOG_URL,
    community: flindBuildEnv.VITE_FLIND_COMMUNITY_URL,
    roadmap: flindBuildEnv.VITE_FLIND_ROADMAP_URL,
    terms: flindBuildEnv.VITE_FLIND_TERMS_URL,
    privacy: flindBuildEnv.VITE_FLIND_PRIVACY_URL,
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

/** A first-party deep link under the operator's explicitly configured docs root.
 * An absent owned docs URL or noncanonical path produces no link, never an
 * inherited upstream/provider destination.
 */
export function flindDocsUrl(
    relativePath: string,
    hostname: string = ownedHostname,
    links: LinkConfig = configuredLinks
): string | null {
    if (
        typeof relativePath !== 'string' ||
        !relativePath ||
        relativePath.length > 250 ||
        !/^[a-z0-9][a-z0-9/_-]*$/.test(relativePath) ||
        relativePath.split('/').some((part) => !part || part === '.' || part === '..')
    ) {
        return null
    }
    const docsRoot = flindPublicUrl('docs', hostname, links)
    if (!docsRoot) {
        return null
    }
    const url = new URL(docsRoot)
    url.pathname = `${url.pathname.replace(/\/$/, '')}/${relativePath}`
    url.search = ''
    return url.toString()
}

/** Optional same-owner docs link to a validated heading. A separate
 * fragment parameter keeps ordinary docs paths unable to smuggle # or ?.
 */
export function flindDocsSectionUrl(
    relativePath: string,
    section: string,
    hostname: string = ownedHostname,
    links: LinkConfig = configuredLinks
): string | null {
    if (typeof section !== 'string' || !/^[a-z0-9][a-z0-9-]{0,99}$/.test(section)) {
        return null
    }
    const docsUrl = flindDocsUrl(relativePath, hostname, links)
    if (!docsUrl) {
        return null
    }
    const url = new URL(docsUrl)
    url.hash = section
    return url.toString()
}

/** No arbitrary URL may flow into dashboard "Learn more" links.
 * Preserve a rendered explanation with no link if Flind docs are absent.
 */
export function isOwnedFlindDocsDestination(
    raw: unknown,
    hostname: string = ownedHostname,
    links: LinkConfig = configuredLinks
): raw is string {
    if (typeof raw !== 'string' || raw !== raw.trim() || raw.endsWith('#')) {
        return false
    }
    const root = flindPublicUrl('docs', hostname, links)
    if (!root) {
        return false
    }
    try {
        const candidate = new URL(raw)
        const owned = new URL(root)
        const docsPath = owned.pathname.replace(/\/$/, '')
        return (
            candidate.protocol === 'https:' &&
            candidate.origin === owned.origin &&
            !candidate.port &&
            !candidate.username &&
            !candidate.password &&
            !candidate.search &&
            candidate.pathname.startsWith(docsPath + '/') &&
            (!candidate.hash || /^#[a-z0-9][a-z0-9-]{0,99}$/.test(candidate.hash))
        )
    } catch {
        return false
    }
}
