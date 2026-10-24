import { LemonTag } from '@flind/lemon-ui'

import type { FeatureRequestStatusEnumApi } from '../../generated/api.schemas'
import { featureRequestStatusLabel, featureRequestStatusTagType } from './featureRequestOptions'

export function FeatureRequestStatusBadge({ status }: { status: FeatureRequestStatusEnumApi }): JSX.Element {
    return (
        <LemonTag size="small" type={featureRequestStatusTagType(status)}>
            {featureRequestStatusLabel(status)}
        </LemonTag>
    )
}
