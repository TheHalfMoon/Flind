import { LemonBanner } from '@flind/lemon-ui'
import { useValues } from 'kea'

import { FEATURE_FLAGS } from 'lib/constants'
import { flindDocsUrl } from 'lib/flindPublicLinks'
import { featureFlagLogic } from 'lib/logic/featureFlagLogic'
import { userLogic } from 'scenes/userLogic'

export function InboxMcpBanner(): JSX.Element | null {
    const { user } = useValues(userLogic)
    const { featureFlags } = useValues(featureFlagLogic)

    const mcpDocs = flindDocsUrl('model-context-protocol')
    if (featureFlags[FEATURE_FLAGS.INBOX_MCP_USED]) {
        return null
    }

    return (
        <LemonBanner
            type="info"
            dismissKey={`inbox-mcp-banner-${user?.uuid ?? 'anonymous'}`}
            className="!bg-fill-info-secondary"
            action={
                mcpDocs
                    ? {
                          children: 'Install Flind MCP',
                          type: 'primary',
                          to: mcpDocs,
                          targetBlank: true,
                          'data-attr': 'inbox-mcp-banner-install',
                      }
                    : undefined
            }
        >
            Use the self-driving inbox with your agents through Flind MCP.
        </LemonBanner>
    )
}
