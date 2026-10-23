import { useValues } from 'kea'
import { router } from 'kea-router'

import { LemonField, LemonSelect } from '@posthog/lemon-ui'

import { flindRegionHost, flindRegionUrl } from 'lib/flindRegionHosts'
import { preflightLogic } from 'scenes/PreflightCheck/preflightLogic'

import { Region } from '~/types'

// Flind is local-first. Only offer multi-region navigation after both
// first-party destinations have been explicitly configured by the operator.
export default function RegionSelect(): JSX.Element | null {
    const { preflight } = useValues(preflightLogic)
    const usHost = flindRegionHost(Region.US)
    const euHost = flindRegionHost(Region.EU)

    if (!preflight?.cloud || !preflight?.region || !usHost || !euHost) {
        return null
    }

    return (
        <LemonField.Pure label="Flind region">
            <LemonSelect
                value={preflight.region}
                options={[
                    { label: 'United States', value: Region.US },
                    { label: 'European Union', value: Region.EU },
                ]}
                fullWidth
                onChange={(region) => {
                    if (!region) {
                        return
                    }
                    const { pathname, search, hash } = router.values.currentLocation
                    const destination = flindRegionUrl(region, `${pathname}${search}${hash}`)
                    if (destination) {
                        window.location.href = destination
                    }
                }}
            />
        </LemonField.Pure>
    )
}
