/** First-party region origins are absent until the Flind operator configures them.
 * Never infer a redirect destination from a cookie, user-controlled URL, or inherited vendor constant.
 */
import { Region } from '~/types'
import { flindBuildEnv } from 'lib/flindBuildEnv'

export type FlindRegionHosts = Partial<Record<Region, string | undefined>>

const CONFIGURED_HOSTS: FlindRegionHosts = {
    [Region.US]: flindBuildEnv.VITE_FLIND_REGION_US_HOST,
    [Region.EU]: flindBuildEnv.VITE_FLIND_REGION_EU_HOST,
}

export function flindRegionHost(region: Region, config: FlindRegionHosts = CONFIGURED_HOSTS): string | null {
    if (region !== Region.US && region !== Region.EU) {
        return null
    }

    const rawHost = config[region]
    if (!rawHost || rawHost !== rawHost.toLowerCase() || rawHost.length > 253) {
        return null
    }

    // Operator input is a bare DNS host, never a URL, port, path, or credential.
    if (!/^[a-z0-9][a-z0-9.-]*[a-z0-9]$/.test(rawHost) || rawHost.includes('..')) {
        return null
    }
    const labels = rawHost.split('.')
    if (labels.some((label) => !label || label.length > 63 || label.startsWith('-') || label.endsWith('-'))) {
        return null
    }
    return rawHost
}

export function flindRegionUrl(
    region: Region,
    path: string,
    config: FlindRegionHosts = CONFIGURED_HOSTS
): string | null {
    const host = flindRegionHost(region, config)
    if (!host || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) {
        return null
    }
    return `https://${host}${path}`
}
