import { useValues } from 'kea'

import { Badge } from '@flind/quill'

import { subscriptionsLogic } from 'products/subscriptions/frontend/components/Subscriptions/subscriptionsLogic'

export function SubscriptionCountBadge({ dashboardId }: { dashboardId: number }): JSX.Element | null {
    const { subscriptions } = useValues(subscriptionsLogic({ dashboardId }))
    const count = subscriptions?.length ?? 0
    return count > 0 ? <Badge>{count}</Badge> : null
}
