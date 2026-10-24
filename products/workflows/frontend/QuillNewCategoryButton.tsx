import { useActions } from 'kea'

import { IconPlus } from '@posthog/icons'
import { Button } from '@flind/quill'

import { optOutCategoriesLogic } from './OptOuts/optOutCategoriesLogic'

export function QuillNewCategoryButton(): JSX.Element {
    const { openNewCategoryModal } = useActions(optOutCategoriesLogic)

    return (
        <Button data-attr="new-optout-category" variant="primary" onClick={() => openNewCategoryModal()}>
            <IconPlus />
            New category
        </Button>
    )
}
