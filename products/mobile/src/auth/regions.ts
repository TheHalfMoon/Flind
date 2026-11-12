import { isInternalBuild, isLoopbackHost } from '@/lib/environment'

import { isInheritedProviderHostname } from './hostSafety'

export type RegionId = 'us' | 'eu' | 'custom'

export interface Region {
    id: RegionId
    label: string
    host: string
    clientId: string
}

export interface CloudRegion extends Region {
    id: Exclude<RegionId, 'custom'>
    flag: string
}

// Flind-owned cloud choices exist only when explicitly configured at build time.
export const US_CLIENT_ID = process.env.EXPO_PUBLIC_FLIND_US_CLIENT_ID?.trim() ?? ''
export const EU_CLIENT_ID = process.env.EXPO_PUBLIC_FLIND_EU_CLIENT_ID?.trim() ?? ''
export const DEV_CLIENT_ID = process.env.EXPO_PUBLIC_FLIND_DEV_CLIENT_ID?.trim() ?? ''

const configuredCloudRegions: readonly CloudRegion[] = [
    { id: 'us', label: 'United States', flag: '🇺🇸', host: process.env.EXPO_PUBLIC_FLIND_US_HOST?.trim() ?? '', clientId: US_CLIENT_ID },
    { id: 'eu', label: 'European Union', flag: '🇪🇺', host: process.env.EXPO_PUBLIC_FLIND_EU_HOST?.trim() ?? '', clientId: EU_CLIENT_ID },
]
export const CLOUD_REGIONS: readonly CloudRegion[] = configuredCloudRegions.filter(
    (region) => Boolean(region.host && region.clientId) && validateHost(region.host, false).ok
)

// The id `custom` is persisted in AsyncStorage by the auth store, so it keeps its name while the label changes.
export const REGIONS: readonly Region[] = [
    ...CLOUD_REGIONS,
    { id: 'custom', label: 'Self-hosted', host: '', clientId: '' },
]

const EUROPEAN_REGION_CODES = new Set([
    'AD',
    'AL',
    'AT',
    'AX',
    'BA',
    'BE',
    'BG',
    'BY',
    'CH',
    'CY',
    'CZ',
    'DE',
    'DK',
    'EE',
    'ES',
    'FI',
    'FO',
    'FR',
    'GB',
    'GG',
    'GI',
    'GR',
    'HR',
    'HU',
    'IE',
    'IM',
    'IS',
    'IT',
    'JE',
    'LI',
    'LT',
    'LU',
    'LV',
    'MC',
    'MD',
    'ME',
    'MK',
    'MT',
    'NL',
    'NO',
    'PL',
    'PT',
    'RO',
    'RS',
    'RU',
    'SE',
    'SI',
    'SJ',
    'SK',
    'SM',
    'TR',
    'UA',
    'VA',
    'XK',
])

export function defaultCloudRegion(
    regionCode: string | null,
    timeZone: string | null,
    previousRegion?: RegionId
): CloudRegion['id'] {
    if (previousRegion && previousRegion !== 'custom') {
        return previousRegion
    }
    if (regionCode) {
        return EUROPEAN_REGION_CODES.has(regionCode.toUpperCase()) ? 'eu' : 'us'
    }
    return timeZone?.startsWith('Europe/') ? 'eu' : 'us'
}

// Store review may not allow a link that leaves the app to create an account, so a build can hide it.
export const SHOW_SIGNUP_LINK = process.env.EXPO_PUBLIC_SIGNUP_LINK !== '0'

export function signupUrl(host: string): string {
    return `${host}/signup`
}

export function regionForHost(host: string): RegionId {
    return REGIONS.find((region) => region.host !== '' && region.host === host)?.id ?? 'custom'
}

export type HostValidation = { ok: true; host: string } | { ok: false; error: string }

// The dev app exists only on a developer's machine, so store builds start the Client ID field empty.
export const DEFAULT_CUSTOM_CLIENT_ID = isInternalBuild ? DEV_CLIENT_ID : ''

// Tokens travel to this host, so plain http is only accepted for loopback addresses, which is also the only place the
// server allows http redirects. Only internal builds accept it, because a local stack is a developer's setup.
export function validateHost(input: string, allowLoopbackHttp: boolean = isInternalBuild): HostValidation {
    const trimmed = input.trim().replace(/\/+$/, '')
    if (!trimmed) {
        return { ok: false, error: 'Enter the address of your Flind instance.' }
    }
    const withScheme = /^[a-z][a-z\d+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`
    let url: URL
    try {
        url = new URL(withScheme)
    } catch {
        return { ok: false, error: "That doesn't look like a web address. Try something like flind.example.com." }
    }
    if (!url.hostname) {
        return { ok: false, error: "That doesn't look like a web address. Try something like flind.example.com." }
    }
    if (isInheritedProviderHostname(url.hostname)) {
        return { ok: false, error: 'Use an endpoint operated by your Flind deployment, not an inherited cloud service.' }
    }
    if (url.username || url.password) {
        return { ok: false, error: 'Remove credentials from the Flind host address.' }
    }
    if (url.protocol === 'http:' && !(allowLoopbackHttp && isLoopbackHost(url.hostname))) {
        return {
            ok: false,
            error: allowLoopbackHttp
                ? 'Use an https address. Plain http only works for localhost.'
                : 'Use an https address, for example https://flind.example.com.',
        }
    }
    if (url.protocol !== 'https:' && url.protocol !== 'http:') {
        return { ok: false, error: 'Use an https address, for example https://flind.example.com.' }
    }
    return { ok: true, host: `${url.protocol}//${url.host}` }
}
