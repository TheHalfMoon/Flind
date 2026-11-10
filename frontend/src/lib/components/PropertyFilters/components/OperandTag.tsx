import { LemonTag } from '@flind/lemon-ui'
import { Badge } from '@flind/quill'

import { useQuillSurface } from 'lib/components/QuillSurface/quillSurfaceContext'

export const OperandTag = ({ operand, className }: { operand: 'and' | 'or'; className?: string }): JSX.Element => {
    const quillSurface = useQuillSurface()

    if (quillSurface) {
        return (
            <Badge variant={operand === 'and' ? 'info' : 'completed'} className={className}>
                <span className="uppercase">{operand}</span>
            </Badge>
        )
    }

    return (
        <LemonTag type={operand === 'and' ? 'highlight' : 'completion'} className={className}>
            <span className="uppercase">{operand}</span>
        </LemonTag>
    )
}
