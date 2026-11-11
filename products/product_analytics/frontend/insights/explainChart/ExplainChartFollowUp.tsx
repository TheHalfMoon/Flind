import { IconMessage } from '@posthog/icons'
import { Button } from '@flind/quill'

export function ExplainChartFollowUp({ onClick }: { onClick: () => void }): JSX.Element {
    return (
        <Button variant="outline" size="sm" onClick={onClick} data-attr="explain-chart-ask-follow-up">
            <IconMessage />
            Ask Flind AI a follow-up
        </Button>
    )
}
