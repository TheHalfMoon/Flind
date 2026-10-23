/**
 * URLs embedded in untrusted data may be automatically loaded or linkified only
 * when their origin exactly matches this Flind frontend. A provider website,
 * sibling subdomain, different scheme, or a port change is NOT first-party.
 */
export function isTrustedFlindUrl(url: string | undefined): boolean {
    if (!url) {
        return false
    }
    try {
        const parsed = new URL(url, window.location.origin)
        return (parsed.protocol === 'https:' || parsed.protocol === 'http:') && parsed.origin === window.location.origin
    } catch {
        return false
    }
}
