import { sidebarProductMeta } from '~/layout/panel-layout/sidebarProductMeta'
import { getTreeItemsProducts } from '~/products'

describe('sidebarProductMeta', () => {
    const products = getTreeItemsProducts()

    it.each(products.map((product) => [product.path, product] as const))(
        '%s explains itself without pointing to inherited vendor documentation',
        (_path, product) => {
            const { description, docsHref } = sidebarProductMeta(product)
            expect(description).toBeTruthy()
            // Flind docs are not published yet. Hide inherited links instead of
            // advertising another provider's feature-specific documentation.
            expect(docsHref).toBeUndefined()
        }
    )
})
