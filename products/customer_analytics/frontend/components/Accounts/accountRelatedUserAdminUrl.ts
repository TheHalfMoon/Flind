import { flindRegionHost, type FlindRegionHosts } from 'lib/flindRegionHosts'

import { Region } from '~/types'

/** Never redirect an admin action to an inherited or unregistered cloud host. */
export function getAccountRelatedUserAdminUrl(
    region: Region.US | Region.EU,
    userId: number,
    currentOrigin: string = window.location.origin,
    configuredHosts?: FlindRegionHosts
): string {
    const currentUrl = new URL(currentOrigin)
    const target = flindRegionHost(region, configuredHosts)
    const ownedRegions = ([Region.US, Region.EU] as const)
        .map((r) => flindRegionHost(r, configuredHosts))
        .filter((host): host is string => !!host)
    const currentIsConfiguredFlindRegion = ownedRegions.some((host) => currentUrl.origin === `https://${host}`)
    const adminOrigin = currentIsConfiguredFlindRegion && target ? `https://${target}` : currentUrl.origin
    return `${adminOrigin}/admin/posthog/user/${userId}/change/`
}
