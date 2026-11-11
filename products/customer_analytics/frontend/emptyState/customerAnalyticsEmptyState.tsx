import { IconPeople } from '@flind/icons'
import * as businessEvolutionPng from '@posthog/brand/hoggies/png/business-evolution'

import { pngHoggie } from 'lib/brand/hoggies'
import type { SceneProductEmptyState } from 'lib/components/ProductEmptyState/types'
import { FEATURE_FLAGS } from 'lib/constants'
import { flindDocsUrl } from 'lib/flindPublicLinks'

import { ProductKey } from '~/queries/schema/schema-general'

import { CustomerAnalyticsPreview } from './CustomerAnalyticsPreview'
import { customerAnalyticsSetupLogic } from './customerAnalyticsSetupLogic'

const HedgehogBusiness = pngHoggie(businessEvolutionPng)
const groupAnalyticsDocs = flindDocsUrl('product-analytics/group-analytics')

export const customerAnalyticsEmptyState: SceneProductEmptyState = {
    statusLogic: customerAnalyticsSetupLogic,
    // The whole product is behind this flag; its feature-preview gate handles the flag-off case.
    featureFlag: FEATURE_FLAGS.CUSTOMER_ANALYTICS,
    config: {
        productKey: ProductKey.CUSTOMER_ANALYTICS,
        productName: 'Customer analytics',
        icon: <IconPeople />,
        accentColor: 'var(--color-product-customer-analytics-light)',
        accentColorDark: 'var(--color-product-customer-analytics-dark)',
        hedgehog: HedgehogBusiness,
        text: {
            'needs-setup': {
                headline: 'See accounts the way you see users',
                lead: "Customer analytics is built on group analytics: group your users into accounts, then follow each account's activity, health, notes, and feature requests in one place. Start by sending group data from your SDK.",
            },
        },
        primaryAction: groupAnalyticsDocs ? { label: 'Set up group analytics', to: groupAnalyticsDocs } : undefined,
        docsUrl: flindDocsUrl('customer-analytics') ?? undefined,
        previewLabel: 'Your accounts, once grouped',
        Preview: CustomerAnalyticsPreview,
    },
}
