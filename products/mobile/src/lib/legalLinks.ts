import { Linking } from 'react-native'

import { isInheritedProviderHostname } from '@/auth/hostSafety'
import { track } from './analytics'

/**
 * Legal and support destinations are supplied only by the Flind deployer.
 * No original-service policy, support contract or URL is represented as Flind's.
 * Unconfigured or invalid destinations are unavailable, not guessed.
 */
export function ownedLegalUrl(value: string | undefined): string | null {
    if (!value?.trim()) return null
    try {
        const parsed = new URL(value.trim())
        if (
            parsed.protocol !== 'https:' ||
            !parsed.hostname ||
            parsed.username ||
            parsed.password ||
            isInheritedProviderHostname(parsed.hostname)
        )
            return null
        return parsed.toString()
    } catch {
        return null
    }
}

export const PRIVACY_POLICY_URL = ownedLegalUrl(process.env.EXPO_PUBLIC_FLIND_PRIVACY_URL)
export const TERMS_URL = ownedLegalUrl(process.env.EXPO_PUBLIC_FLIND_TERMS_URL)
export const SUPPORT_URL = ownedLegalUrl(process.env.EXPO_PUBLIC_FLIND_SUPPORT_URL)

/** The authenticated web app's own delete-account section. */
export function deleteAccountUrl(host: string): string {
    return `${host}/settings/user-danger-zone`
}

export type LegalLink = 'privacy' | 'terms' | 'support' | 'delete_account'

export function openLegalLink(link: LegalLink, url: string | null, surface: 'sign_in' | 'settings'): void {
    if (url === null) return
    track('mobile_legal_link_opened', { link, surface })
    Linking.openURL(url).catch(() => undefined)
}
