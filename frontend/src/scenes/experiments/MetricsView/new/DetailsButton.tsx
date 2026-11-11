import { IconGraph } from '@flind/icons'
import { LemonButton } from '@flind/lemon-ui'

import { ExperimentMetric } from '~/queries/schema/schema-general'

export function DetailsButton({
    setIsModalOpen,
}: {
    metric: ExperimentMetric
    setIsModalOpen: (isOpen: boolean) => void
}): JSX.Element {
    return (
        <>
            <LemonButton type="secondary" size="xsmall" icon={<IconGraph />} onClick={() => setIsModalOpen(true)}>
                Details
            </LemonButton>
        </>
    )
}
