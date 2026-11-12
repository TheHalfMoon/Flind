import { randomString } from '../utils'
import { expect, test } from '../utils/workspace-test-base'

const PROXY_BASE_URL = process.env.E2E_PROXY_URL || 'http://localhost:8010'
const SDK_HOST_PATH = '/flind-browser-sdk-ingestion-e2e'

// This page uses the same locally served posthog-js snippet as the toolbar E2E.
// The backend and capture consumer must be started via the opt-in ingestion workflow.
function sdkHostPage(apiToken: string): string {
    return `<!doctype html>
<html>
    <head><script src="/static/array.js"></script></head>
    <body>
        <script>
            window.__flind_sdk_smoke_ready = false;
            posthog.init(${JSON.stringify(apiToken)}, {
                api_host: window.location.origin,
                autocapture: false,
                // Playwright Chromium is a bot by definition; do not drop this synthetic E2E event.
                // This applies only to the test page, not Flind's default SDK configuration.
                opt_out_useragent_filter: true,
                capture_pageview: false,
                capture_pageleave: false,
                disable_session_recording: true,
                advanced_disable_decide: true,
                request_batching: false,
                disable_persistence: true,
                loaded: function() {
                    window.__flind_sdk_smoke_ready = true;
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
        const captureResponses: string[] = []
        const captureFailures: string[] = []
        const isCaptureRequest = (url: string): boolean => /\/(e|batch|capture|i\/v0\/e)\/?$/.test(new URL(url).pathname)
        // Diagnostics are intentionally restricted to method/path/status, never tokens or event payloads.
        page.on('response', (resp) => {
            if (isCaptureRequest(resp.url()) && resp.request().method() === 'POST') {
                captureResponses.push(`${new URL(resp.url()).pathname}: ${resp.status()}`)
            }
        })
        page.on('requestfailed', (req) => {
            if (isCaptureRequest(req.url())) {
                captureFailures.push(`${new URL(req.url()).pathname}: ${req.failure()?.errorText ?? 'unknown'}`)
            }
        })
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
            (route) => route.fulfill({ contentType: 'text/html', body: sdkHostPage(apiToken) })
        )

        await page.goto(`${PROXY_BASE_URL}${SDK_HOST_PATH}`)
        await expect
            .poll(
                () => page.evaluate(() => (window as Window & { __flind_sdk_smoke_ready?: boolean }).__flind_sdk_smoke_ready),
                { timeout: 30_000 }
            )
            .toBe(true)

        const configuredHost = await page.evaluate(() => {
            const sdk = (window as unknown as { posthog: { config: { api_host: string } } }).posthog
            return sdk.config.api_host
        })
        expect(new URL(configuredHost).origin).toBe(new URL(PROXY_BASE_URL).origin)
        // Capture only after the SDK's loaded callback, rather than racing its initialization.
        const captureState = await page.evaluate((name) => {
            const sdk = (window as unknown as {
                posthog: {
                    __loaded?: boolean
                    is_capturing: () => boolean
                    capture: (event: string, properties: Record<string, unknown>) => unknown
                }
            }).posthog
            const isCapturing = sdk.is_capturing()
            const result = sdk.capture(name, { flind_sdk_ingestion_test: true })
            // Return only booleans; do not expose project tokens or event payloads in CI logs.
            return { loaded: sdk.__loaded === true, isCapturing, accepted: result !== undefined }
        }, eventName)
        expect(captureState, 'SDK refused the synthetic Playwright capture').toEqual({
            loaded: true,
            isCapturing: true,
            accepted: true,
        })
        try {
            await expect.poll(
                () => captureResponses.some((r) => /: 2\d\d$/.test(r)) ? 1 : 0,
                { timeout: 25_000, intervals: [1_000, 2_000] }
            ).toBeGreaterThan(0)
        } catch {
            throw new Error(`SDK capture did not return HTTP 2xx. Requests: ${JSON.stringify(captureResponses)}; failures: ${JSON.stringify(captureFailures)}; blocked origins: ${JSON.stringify([...externalOrigins])}`)
        }
        expect([...externalOrigins], 'browser SDK requested an external host').toEqual([])

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
