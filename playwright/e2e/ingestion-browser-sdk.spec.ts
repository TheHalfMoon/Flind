import { randomString } from '../utils'
import { expect, test } from '../utils/workspace-test-base'

const PROXY_BASE_URL = process.env.E2E_PROXY_URL || 'http://localhost:8010'
const SDK_HOST_PATH = '/flind-browser-sdk-ingestion-e2e'

// This page uses the same locally served posthog-js snippet as the toolbar E2E.
// The backend and capture consumer must be started via the opt-in ingestion workflow.
function sdkHostPage(apiToken: string, eventName: string): string {
    return `<!doctype html>
<html>
    <head><script src="/static/array.js"></script></head>
    <body>
        <script>
            window.__flind_sdk_smoke_ready = false;
            posthog.init(${JSON.stringify(apiToken)}, {
                api_host: window.location.origin,
                autocapture: false,
                capture_pageview: false,
                capture_pageleave: false,
                disable_session_recording: true,
                advanced_disable_decide: true,
                request_batching: false,
                disable_persistence: true,
                loaded: function(client) {
                    window.__flind_sdk_smoke_ready = true;
                    client.capture(${JSON.stringify(eventName)}, { flind_sdk_ingestion_test: true });
                }
            });
        </script>
    </body>
</html>`
}

test.describe('Flind browser SDK ingestion', () => {
    test('browser SDK capture becomes queryable without contacting external hosts', async ({ page, request, playwrightSetup }) => {
        test.setTimeout(180_000)
        const host = new URL(PROXY_BASE_URL).hostname
        expect(['localhost', '127.0.0.1']).toContain(host)
        const workspace = await playwrightSetup.createWorkspace({ skip_onboarding: true, no_demo_data: true })
        const authHeaders = { Authorization: `Bearer ${workspace.personal_api_key}` }
        const eventName = randomString('flind_browser_sdk_')

        const team = await request.get(`/api/environments/${workspace.team_id}/`, { headers: authHeaders })
        expect(team.ok()).toBe(true)
        const apiToken: string = (await team.json()).api_token
        expect(apiToken.length).toBeGreaterThan(0)

        const externalOrigins = new Set<string>()
        // Block off-instance traffic before it can carry credentials or event data.
        await page.route('**/*', async (route) => {
            const url = new URL(route.request().url())
            if (!['localhost', '127.0.0.1'].includes(url.hostname)) {
                externalOrigins.add(url.origin)
                await route.abort()
                return
            }
            await route.continue()
        })
        await page.route(
            (url) => url.pathname === SDK_HOST_PATH,
            (route) => route.fulfill({ contentType: 'text/html', body: sdkHostPage(apiToken, eventName) })
        )

        await page.goto(`${PROXY_BASE_URL}${SDK_HOST_PATH}`)
        await expect
            .poll(
                () => page.evaluate(() => (window as Window & { __flind_sdk_smoke_ready?: boolean }).__flind_sdk_smoke_ready),
                { timeout: 30_000 }
            )
            .toBe(true)

        await expect
            .poll(
                async () => {
                    const resp = await request.post(`/api/environments/${workspace.team_id}/query/`, {
                        headers: authHeaders,
                        data: {
                            refresh: 'force_blocking',
                            query: {
                                kind: 'HogQLQuery',
                                query: `SELECT count() FROM events WHERE event = '${eventName}'`,
                            },
                        },
                    })
                    if (!resp.ok()) {
                        throw new Error(`Flind browser SDK ingestion query returned ${resp.status()}: ${await resp.text()}`)
                    }
                    const body = await resp.json()
                    return Number(body.results?.[0]?.[0] ?? 0)
                },
                { timeout: 90_000, intervals: [2_000, 5_000] }
            )
            .toBeGreaterThan(0)
        expect(Array.from(externalOrigins), 'browser SDK requested an external host').toEqual([])
    })
})
