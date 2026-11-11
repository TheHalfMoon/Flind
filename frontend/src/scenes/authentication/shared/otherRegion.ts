import { FlindRegionHosts, flindRegionHost } from 'lib/flindRegionHosts'

import { Region } from '~/types'

export function otherRegionOf(region: Region): Region {
    return region === Region.US ? Region.EU : Region.US
}

// Preserve the query string (e.g. `next`) but always land on the login page of the other region.
// Flind only links to a region host its operator configured; without one there is no other region to offer.
export function otherRegionLoginUrl(region: Region, search: string, config?: FlindRegionHosts): string | null {
    const host = flindRegionHost(otherRegionOf(region), config)
    return host ? `https://${host}/login${search}` : null
}
