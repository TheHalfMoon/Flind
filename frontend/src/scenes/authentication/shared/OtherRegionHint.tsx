import { useValues } from 'kea'

import { LemonBanner } from 'lib/lemon-ui/LemonBanner'
import { Link } from 'lib/lemon-ui/Link'
import { flindRegionHost, flindRegionUrl, type FlindRegionHosts } from 'lib/flindRegionHosts'
import { preflightLogic } from 'scenes/PreflightCheck/preflightLogic'

import { Region } from '~/types'

export function otherRegionOf(region: Region): Region {
    return region === Region.US ? Region.EU : Region.US
}

export function otherRegionLoginUrl(region: Region, search: string, config?: FlindRegionHosts): string | null {
    return flindRegionUrl(otherRegionOf(region), `/login${search}`, config)
}

// Without Flind-owned region endpoints this hint stays hidden: never offer
// an unrelated cloud as the location of a user's Flind account.
export function OtherRegionHint(): JSX.Element | null {
    const { preflight } = useValues(preflightLogic)
    if (!preflight?.cloud || !preflight?.region) {
        return null
    }

    const region = otherRegionOf(preflight.region)
    const hostname = flindRegionHost(region)
    const url = otherRegionLoginUrl(preflight.region, location.search)
    if (!hostname || !url) {
        return null
    }

    return (
        <LemonBanner type="info">
            Your Flind account may be in the {region} region. You're currently on {preflight.region}.{' '}
            <Link to={url} disableClientSideRouting data-attr="other-region-login">
                Log in on {hostname}
            </Link>
        </LemonBanner>
    )
}
