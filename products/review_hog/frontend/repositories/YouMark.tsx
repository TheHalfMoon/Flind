import { LemonTag } from '@flind/lemon-ui'

/** Marks a value the viewer set themselves. It sits after the control and takes no space when the value is inherited. */
export function YouMark({ shown }: { shown: boolean }): JSX.Element | null {
    return shown ? (
        <LemonTag type="highlight" size="small" title="Your own choice">
            you
        </LemonTag>
    ) : null
}
