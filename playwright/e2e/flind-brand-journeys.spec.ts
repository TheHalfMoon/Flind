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

    // Neutral until Flind ships its own SDK packages (rename stage 3); it must not claim a Flind SDK yet.
    test('SDK onboarding uses neutral SDK copy', async ({ page }) => {
        await page.goto('/onboarding/product_analytics?step=install&sdk=react')
        // The install step leads with the setup wizard; the SDK snippet is behind manual setup.
        // Manual setup opens the SDK grid in a dialog; each SDK card is identified by its logo.
        await page.getByRole('button', { name: 'Need to set up manually?' }).click()
        await page.getByRole('dialog').getByAltText('React logo').click()

        await expect(
            page.getByRole('heading', { name: 'Send React data to Flind using the integration SDK' })
        ).toBeVisible()
        await expect(page.getByText('Read the SDK documentation')).toBeVisible()
    })

    test('billing renders without legal claims attached to Flind', async ({ page }) => {
        await page.goto('/organization/billing')

        await expect(page.getByRole('tab', { name: 'Overview' })).toBeVisible()
        await expect(page.getByRole('heading', { name: 'Products' })).toBeVisible()
        await expect(page.locator('body')).not.toContainText(FLIND_LEGAL_CLAIM)
    })

    test('connected integrations settings render', async ({ page }) => {
        // Project-level integrations are where Slack, GitHub and Linear connections are managed; the
        // organization-level list renders nothing until an organization integration exists.
        await page.goto('/settings/project-integrations')

        for (const title of ['Slack integration', 'GitHub integration', 'Linear integration']) {
            await expect(page.getByRole('heading', { name: title })).toBeVisible()
        }
        await expect(page.locator('body')).not.toContainText(FLIND_LEGAL_CLAIM)
    })
})
