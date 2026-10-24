/**
 * First-party identity for optional external image fetching. Do not impersonate
 * the inherited vendor or invent a Flind-hosted identity directory.
 */
export const BOT_NAME = 'FlindImageFetcherBot'

export function flindImageBotIdentityOrigin(raw = process.env.FLIND_IMAGE_FETCHER_IDENTITY_ORIGIN): string | null {
    if (raw === undefined || raw === '') {
        return null
    }
    if (raw.trim() !== raw) {
        throw new Error('FLIND_IMAGE_FETCHER_IDENTITY_ORIGIN must be a clean HTTPS origin')
    }
    let url: URL
    try {
        url = new URL(raw)
    } catch {
        throw new Error('FLIND_IMAGE_FETCHER_IDENTITY_ORIGIN must be a valid absolute HTTPS origin')
    }
    const host = url.hostname.toLowerCase().replace(/\.+$/, '')
    if (
        url.protocol !== 'https:' ||
        host === 'posthog.com' ||
        host.endsWith('.posthog.com') ||
        !host ||
        url.username ||
        url.password ||
        url.pathname !== '/' ||
        url.search ||
        url.hash
    ) {
        throw new Error('FLIND_IMAGE_FETCHER_IDENTITY_ORIGIN must be an approved Flind-owned HTTPS origin')
    }
    return url.origin
}

const identityOrigin = flindImageBotIdentityOrigin()

export const REQUEST_IDENTITY_HEADERS: Readonly<Record<string, string>> = {
    'user-agent': BOT_NAME + '/1.0',
    ...(identityOrigin ? { referer: identityOrigin + '/' } : {}),
}

export function flindSignatureAgentHeader(): string {
    const origin = flindImageBotIdentityOrigin()
    if (!origin) {
        throw new Error('FLIND_IMAGE_FETCHER_IDENTITY_ORIGIN is required for Web Bot Auth signing')
    }
    return JSON.stringify(origin + '/.well-known/http-message-signatures-directory')
}
