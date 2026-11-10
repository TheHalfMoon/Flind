import { useActions, useValues } from 'kea'

import { IconExternal } from '@posthog/icons'
import { LemonButton, LemonSwitch } from '@flind/lemon-ui'

import { useRestrictedArea } from 'lib/components/RestrictedArea'
import { OrganizationMembershipLevel } from 'lib/constants'
import { organizationLogic } from 'scenes/organizationLogic'

import { AI_TRAINING_URL } from './aiTrainingConstants'
import { ORG_ADMIN_REQUIRED_TOOLTIP } from './organizationSettingsConstants'

export function AITrainingDescription({ hasSignedBaa, isLocked }: { hasSignedBaa: boolean; isLocked: boolean }): JSX.Element {
    if (hasSignedBaa) {
        return (
            <p className="mb-2 text-sm text-secondary">
                You are opted out of internal AI training because your organization has a signed BAA.
            </p>
        )
    }

    if (isLocked) {
        return (
            <p className="mb-2 text-sm text-secondary">
                Your organization's internal AI training preference is fixed by your contract and cannot be changed.
                Contact your Flind administrator if you need to discuss this.
            </p>
        )
    }

    return (
        <div className="mb-2 text-sm text-secondary">
            <p>
                Allow anonymized, aggregated data from this organization to be used to train AI features. How
                that data is handled depends on how this Flind instance is operated.
            </p>
            <p className="mt-2">Opting out means that you cannot access certain AI features.</p>
        </div>
    )
}

export function OrganizationAITrainingOptOut(): JSX.Element {
    const { currentOrganization, currentOrganizationLoading } = useValues(organizationLogic)
    const { updateOrganization } = useActions(organizationLogic)

    const restrictionReason = useRestrictedArea({ minimumAccessLevel: OrganizationMembershipLevel.Admin })
    const hasSignedBaa = !!currentOrganization?.has_signed_baa
    const isLocked = !!currentOrganization?.is_ai_training_locked

    const disabledReason = hasSignedBaa
        ? 'Organizations with a signed BAA stay opted out of AI training. Contact your Flind administrator if this needs to change.'
        : isLocked
          ? 'Contact your Flind administrator to change this setting.'
          : restrictionReason
            ? ORG_ADMIN_REQUIRED_TOOLTIP
            : undefined

    const checked = !hasSignedBaa && !!currentOrganization?.is_ai_training_opted_in

    return (
        <div className="max-w-160">
            <AITrainingDescription hasSignedBaa={hasSignedBaa} isLocked={isLocked} />
            <div className="my-4">
                <LemonSwitch
                    label="Enable AI training on anonymized data"
                    data-attr="organization-ai-training-opt-in"
                    onChange={(value) => {
                        updateOrganization({ is_ai_training_opted_in: value })
                    }}
                    checked={checked}
                    disabledReason={disabledReason}
                    loading={currentOrganizationLoading}
                    bordered
                />
            </div>
            <LemonButton type="primary" className="inline-block" sideIcon={<IconExternal />} to={AI_TRAINING_URL}>
                What's this?
            </LemonButton>
        </div>
    )
}
