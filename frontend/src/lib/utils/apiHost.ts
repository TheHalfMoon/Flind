import { getBackendHost } from 'lib/oauth/oauthClient'

import { inStorybook, inStorybookTestRunner } from './dom'
import { getAppContext } from './getAppContext'

/**
 * Resolve a backend-served asset path (e.g. `/uploaded_media/<id>`) to a full URL. These resources
 * live on the backend, not the SPA bundle's origin — so in OAuth mode, where the app runs against a
 * remote region, prefix that region's host. Same-origin (session) mode returns the path unchanged.
 * Already-absolute URLs and `data:` URIs pass through untouched.
 */
export function backendAssetUrl(path: string): string {
    if (/^(https?:|data:)/.test(path)) {
        return path
    }
    const backendHost = getBackendHost()
    return backendHost ? `${backendHost}${path}` : path
}

export function apiHostOrigin(): string {
    // Flind never redirects ingestion to a provider's inherited cloud URL.
    return window.location.origin
}

export function liveEventsHostOrigin(): string | null {
    const appContext = getAppContext()

    if (inStorybook() || inStorybookTestRunner()) {
        return 'http://localhost:6006'
    }

    return appContext?.livestream_host || 'http://localhost:8666'
}

export function publicWebhooksHostOrigin(): string | null {
    return window.location.origin
}
