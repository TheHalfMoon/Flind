import { expect, test } from '../utils/workspace-test-base'

// Flind is self-hosted software, not a contracting party or data custodian. These journeys check
// that the rebranded screens render in a real browser against a real backend, and that none of
// them attaches a BAA, DPA, subprocessor or data-custody claim to Flind.
const FLIND_LEGAL_CLAIM = /(BAA|DPA|agreement|subprocessor)[^.]*with Flind|stays with Flind|Flind subprocessors/i

test.describe('Flind rebranded journeys', () => {
    test.beforeEach(async ({ page, playwrightSetup }) => {
        const workspace = await playwrightSetup.createWorkspace({ skip_onboarding: true, no_demo_data: true })
        await playwrightSetup.loginAndNavigateToTeam(page, workspace)
    })

    test('organization AI settings use deployment-neutral copy', async ({ page }) => {
        await page.goto('/settings/organization-details#organization-ai-training-opt-out')

        await expect(
            page
                .getByText(
                    /depends on how this Flind instance is operated|your organization has a signed BAA|Contact your Flind administrator/
                )
                .first()
        ).toBeVisible()
        await expect(page.locator('body')).not.toContainText(FLIND_LEGAL_CLAIM)
    })

    test('impersonation setting refers to staff users of this instance', async ({ page }) => {
        await page.goto('/settings/user-customization')

        await expect(page.getByText(/Staff users of this Flind instance may need to log in as you/)).toBeVisible()
        await expect(page.locator('body')).not.toContainText(/Flind support staff/)
    })

    test('SDK onboarding names the PostHog SDK that sends data to Flind', async ({ page }) => {
        await page.goto('/onboarding/product_analytics?step=install&sdk=react')

        await expect(page.getByRole('heading', { name: 'Send React data to Flind with the PostHog SDK' })).toBeVisible()
        await expect(page.getByText('Read the PostHog SDK docs')).toBeVisible()
    })

    test('billing renders without legal claims attached to Flind', async ({ page }) => {
        await page.goto('/organization/billing')

        await expect(page.getByRole('heading', { name: /Billing/ }).first()).toBeVisible()
        await expect(page.locator('body')).not.toContainText(FLIND_LEGAL_CLAIM)
    })

    test('organization integrations settings render', async ({ page }) => {
        await page.goto('/settings/organization-integrations')

        await expect(page.getByRole('heading', { name: 'Integrations' }).first()).toBeVisible()
        await expect(page.locator('body')).not.toContainText(FLIND_LEGAL_CLAIM)
    })
})
