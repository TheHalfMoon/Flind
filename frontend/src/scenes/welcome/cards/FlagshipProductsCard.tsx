import { useActions } from 'kea'

import { ProductHogHero } from 'lib/components/NavPanelAdvertisement/navPanelAdShared'
import { getProductPushDisplay } from 'lib/components/NavPanelAdvertisement/navPanelProductPushDisplay'
import { LemonCard } from 'lib/lemon-ui/LemonCard'
import { Link } from 'lib/lemon-ui/Link'

import { brandingForProduct } from '../productBranding'
import { welcomeDialogLogic } from '../welcomeDialogLogic'

// The products we want every new account exploring. Both keys resolve in PRODUCT_BRANDING (label +
// docs) and PRODUCT_PUSH_DISPLAY (hog illustration + brand accent + tagline), so the showcase reuses
// the same product illustration and text as the navigation preview.
const FLAGSHIP_PRODUCT_KEYS = [
    'product_analytics',
    'web_analytics',
    'session_replay',
    'error_tracking',
    'llm_analytics',
] as const

export function FlagshipProductsCard(): JSX.Element {
    const { trackCardClick } = useActions(welcomeDialogLogic)

    return (
        <LemonCard hoverEffect={false} className="p-4">
            <h2 className="text-lg font-semibold mb-1">What you get with Flind</h2>
            <p className="text-xs text-muted mb-3 m-0">
                Explore the products available on this Flind instance.
            </p>
            <div className="grid grid-cols-2 gap-2">
                {FLAGSHIP_PRODUCT_KEYS.map((productKey) => {
                    const display = getProductPushDisplay(productKey)
                    const meta = brandingForProduct(productKey)
                    const content = <ProductHogHero hero={display} title={meta.label} text={display.tagline} />
                    const cardClass = 'overflow-hidden rounded border bg-surface-primary text-xs shadow-sm'

                    return meta.docsHref ? (
                        <Link
                            key={productKey}
                            to={meta.docsHref}
                            target="_blank"
                            subtle
                            onClick={() => trackCardClick('products', meta.docsHref)}
                            className={`${cardClass} transition-shadow hover:shadow-md`}
                            data-attr={`welcome-flagship-${productKey}`}
                        >
                            {content}
                        </Link>
                    ) : (
                        <div
                            key={productKey}
                            className={cardClass}
                            data-attr={`welcome-flagship-${productKey}`}
                        >
                            {content}
                        </div>
                    )
                })}
            </div>
        </LemonCard>
    )
}
