import { LemonBanner } from '@flind/lemon-ui'

import { FlindDocsLink } from 'lib/components/FlindDocsLink/FlindDocsLink'

export function SessionAnalysisWarning(): JSX.Element {
    return (
        <LemonBanner type="info" className="mb-4">
            When using sessions and session properties, events without session IDs will be excluded from the set of
            results. <FlindDocsLink path="user-guides/sessions">Learn more about sessions.</FlindDocsLink>
        </LemonBanner>
    )
}
