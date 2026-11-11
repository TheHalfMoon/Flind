import { Box } from '@stripe/ui-extension-sdk/ui'

import type { PostHogClient } from '../posthog/client'
import PromoBanner, { PromoBannerPrimaryLink, PromoBannerText, PromoBannerTitle } from './components/PromoBanner'

interface Props {
    client: PostHogClient | null
    projectId: string | null
}

const SupportTab = ({ client, projectId }: Props): JSX.Element => {
    const posthogBase = client ? `${client.baseUrl}/project/${projectId}` : null

    return (
        <Box css={{ width: 'fill', padding: 'large' }}>
            <PromoBanner hero>
                <PromoBannerTitle>Support is coming to Flind</PromoBannerTitle>
                <PromoBannerText>
                    Soon you'll be able to correlate your Flind users with Stripe customers and respond to support
                    tickets directly from Flind — with full context from session replays, feature flags, and product
                    analytics already attached.
                </PromoBannerText>
                {posthogBase && (
                    <PromoBannerPrimaryLink href={`${posthogBase}/support`}>
                        Learn more about Flind Support
                    </PromoBannerPrimaryLink>
                )}
            </PromoBanner>
        </Box>
    )
}

export default SupportTab
