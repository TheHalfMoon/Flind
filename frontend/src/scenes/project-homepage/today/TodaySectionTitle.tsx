import { Text } from '@flind/quill'

export function TodaySectionTitle({ id, children }: { id?: string; children: string }): JSX.Element {
    return (
        <Text size="base" weight="semibold" render={<h2 id={id} />}>
            {children}
        </Text>
    )
}
