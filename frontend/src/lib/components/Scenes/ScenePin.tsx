import { IconPin, IconPinFilled } from '@flind/icons'

import { ButtonPrimitive } from 'lib/ui/Button/ButtonPrimitives'

import { SceneDataAttrKeyProps } from './utils'

interface ScenePinProps extends SceneDataAttrKeyProps {
    onClick: () => void
    isPinned: boolean
}

export function ScenePin({ dataAttrKey, onClick, isPinned }: ScenePinProps): JSX.Element {
    return (
        <ButtonPrimitive
            menuItem
            onClick={onClick}
            data-attr={`${dataAttrKey}-pin-button`}
            tooltip={isPinned ? 'Unpin' : 'Pin'}
        >
            {isPinned ? <IconPinFilled className="text-warning" /> : <IconPin />}
            Pin
        </ButtonPrimitive>
    )
}
