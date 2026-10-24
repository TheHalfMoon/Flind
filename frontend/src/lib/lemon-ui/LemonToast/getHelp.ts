import { flindPublicUrl } from 'lib/flindPublicLinks'

export type GetHelpAction = () => void

/**
 * A standalone error-toast fallback when the in-app Flind support panel is unavailable.
 * Public documentation must be configured for this Flind instance; never route
 * errors, campaign data, or support requests to an inherited third-party site.
 */
export function openSupportOptions(utmCampaign: string = 'error-toast'): void {
    const docsUrl = flindPublicUrl('docs')
    if (!docsUrl) {
        return
    }

    const target = new URL(docsUrl)
    target.searchParams.set('utm_medium', 'in-product')
    target.searchParams.set('utm_campaign', utmCampaign)
    window.open(target.toString(), '_blank', 'noopener,noreferrer')
}

let getHelpAction: GetHelpAction = openSupportOptions

/**
 * Replaces what the error toast's "Get help" button does. The app registers the in-product support
 * form in `bootApp()`; bundles without one (toolbar, exporter) keep the docs fallback.
 * A seam rather than a direct call because `supportLogic` already imports the toast module, so
 * reaching back into it from here would close a cycle.
 */
export function setGetHelpAction(action: GetHelpAction): void {
    getHelpAction = action
}

/** Restores the docs fallback. Test-only: keeps a registered action from leaking across tests. */
export function resetGetHelpAction(): void {
    getHelpAction = openSupportOptions
}

export function getHelp(): void {
    getHelpAction()
}
