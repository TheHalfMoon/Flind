import { useActions } from 'kea'
import posthog from 'posthog-js'
import { ReactNode } from 'react'

import { useOnMountEffect } from 'lib/hooks/useOnMountEffect'
import { WizardHog } from 'scenes/onboarding/shared/wizardHog'

import { BannerCallout } from './BannerCallout'
import { errorTrackingBannersLogic } from './errorTrackingBannersLogic'
import { sourceMapsExamplesLogic } from './sourceMapsExamplesLogic'
import { SourceMapsExamplesModal } from './SourceMapsExamplesModal'
import { SOURCE_MAPS_PLATFORM_LABELS } from './sourceMapsPlatforms'
import type { SourceMapsRecommendation } from './types'

// Mounts only while the banner is visible, so the "shown" event fires exactly when it was seen.
export function SourceMapsBanner({
    recommendation,
    navigation,
}: {
    recommendation: SourceMapsRecommendation
    navigation?: ReactNode
}): JSX.Element {
    const { openExamples } = useActions(sourceMapsExamplesLogic)
    const { dismissBanner } = useActions(errorTrackingBannersLogic)
    const platform = recommendation.meta.platform ?? 'javascript'
    const labels = SOURCE_MAPS_PLATFORM_LABELS[platform]
    const percent = Math.round((recommendation.meta.unresolved_pct ?? 0) * 100)

    useOnMountEffect(() => {
        posthog.capture('error_tracking_source_maps_banner_shown', {
            unresolved_pct: percent,
            lookback_hours: recommendation.meta.lookback_hours,
            platform,
        })
    })

    return (
        <>
            <BannerCallout
                illustration={WizardHog}
                title={`${percent}% of ${labels.platform} frames that need ${labels.symbols} are missing them`}
                description={
                    <>
                        Upload {labels.symbols} only through a source-map upload method verified for your Flind instance.
                        Check the unresolved frames below to identify the affected files.
                    </>
                }
                primaryAction={{
                    label: 'See missing frames',
                    onClick: () => openExamples(platform),
                    dataAttr: 'error-tracking-source-maps-banner-examples',
                }}
                navigation={navigation}
                onDismiss={() => dismissBanner('source_maps')}
            />
            <SourceMapsExamplesModal />
        </>
    )
}
