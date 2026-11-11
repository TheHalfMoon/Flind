import { useActions, useValues } from 'kea'

import { IconSparkles } from '@flind/icons'
import { LemonButton } from '@flind/lemon-ui'

import { emailDomainAgentLogic } from '../emailDomainAgentLogic'

export function AgentSetupButton(): JSX.Element | null {
    const { agentSetupEnabled } = useValues(emailDomainAgentLogic)
    const { openAgentModal } = useActions(emailDomainAgentLogic)
    if (!agentSetupEnabled) {
        return null
    }
    return (
        <LemonButton
            type="tertiary"
            icon={<IconSparkles />}
            onClick={openAgentModal}
            data-attr="email-domain-agent-setup"
        >
            Let an agent do it
        </LemonButton>
    )
}
