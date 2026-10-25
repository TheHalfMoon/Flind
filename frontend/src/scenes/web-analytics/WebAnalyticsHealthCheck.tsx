import { useValues } from 'kea'

import { LemonBanner } from 'lib/lemon-ui/LemonBanner'
import { flindPublicUrl } from 'lib/flindPublicLinks'
import { Link } from 'lib/lemon-ui/Link'
import { webAnalyticsLogic } from 'scenes/web-analytics/webAnalyticsLogic'

import { ConversionGoalWarning, ProductTab } from './common'

export const WebAnalyticsHealthCheck = (): JSX.Element | null => {
    const { conversionGoalWarning, productTab } = useValues(webAnalyticsLogic)
    const docsUrl = flindPublicUrl('docs')

    if (productTab === ProductTab.MARKETING || productTab === ProductTab.HEALTH) {
        return null
    }

    if (conversionGoalWarning) {
        switch (conversionGoalWarning) {
            case ConversionGoalWarning.CustomEventWithNoSessionId:
                return (
                    <LemonBanner type="warning" className="mt-2">
                        <p>
                            A custom event has been set as a conversion goal, but it has been seen with no{' '}
                            <code>$session_id</code>. This means that some queries will not be able to include these
                            events.
                        </p>
                        <p>
                            To fix this, include a valid <code>$session_id</code> on conversion events.
                            {docsUrl && (
                                <>
                                    {' '}See{' '}
                                    <Link to={docsUrl}>documentation for custom session IDs</Link>.
                                </>
                            )}
                        </p>
                    </LemonBanner>
                )
        }
    }

    return null
}
