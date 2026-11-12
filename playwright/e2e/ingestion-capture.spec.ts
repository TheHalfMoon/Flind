import { randomString } from '../utils'
import { parseHogQLCount } from '../utils/parse-hogql-count'
import { expect, test } from '../utils/workspace-test-base'

// Capture and flags are served by separate Rust services fronted by the Caddy dev proxy,
// not by the Django server Playwright's baseURL points at.
const PROXY_BASE_URL = process.env.E2E_PROXY_URL || 'http://localhost:8010'

test.describe('Event ingestion', () => {
    test('an event sent to the real capture endpoint becomes queryable', async ({ request, playwrightSetup }) => {
        test.setTimeout(180_000)
        const workspace = await playwrightSetup.createWorkspace({ skip_onboarding: true, no_demo_data: true })
        const eventName = randomString('e2e_ingestion_')
        const authHeaders = { Authorization: `Bearer ${workspace.personal_api_key}` }
        let apiToken = ''

        await test.step('fetch the team api token', async () => {
            const team = await request.get(`/api/environments/${workspace.team_id}/`, { headers: authHeaders })
            expect(team.ok()).toBe(true)
            apiToken = (await team.json()).api_token
        })

        await test.step('send an event through the capture endpoint', async () => {
            const captured = await request.post(`${PROXY_BASE_URL}/e/`, {
                data: {
                    api_key: apiToken,
                    event: eventName,
                    distinct_id: randomString('e2e-user-'),
                    timestamp: new Date().toISOString(),
                },
            })
            expect(captured.ok()).toBe(true)
        })

        await test.step('poll until the event has been ingested and is queryable', async () => {
            await expect
                .poll(
                    async () => {
                        const resp = await request.post(`/api/environments/${workspace.team_id}/query/`, {
                            headers: authHeaders,
                            data: {
                                // Without this the endpoint serves a cached result for up to 5 minutes,
                                // so the first poll's zero would be replayed for the rest of the window.
                                refresh: 'force_blocking',
                                query: {
                                    kind: 'HogQLQuery',
                                    query: `SELECT count() FROM events WHERE event = '${eventName}'`,
                                },
                            },
                        })
                        // A 4xx other than rate limiting means the query itself is bad — waiting won't fix it.
                        if (resp.status() >= 400 && resp.status() < 500 && resp.status() !== 429) {
                            throw new Error(`query endpoint returned ${resp.status()}: ${await resp.text()}`)
                        }
                        const body = await resp.json()
                        return Number(body.results?.[0]?.[0] ?? 0)
                    },
                    { timeout: 90_000, intervals: [2_000, 5_000] }
                )
                .toBeGreaterThan(0)
        })

        await test.step('another organization cannot query the captured event', async () => {
            // The positive capture/query assertion above establishes the event is committed.
            // Now query the same event using a completely separate Flind workspace.
            // A zero result is meaningful only after the original tenant can see it.
            const other = await playwrightSetup.createWorkspace({ skip_onboarding: true, no_demo_data: true })
            expect(other.team_id).not.toBe(workspace.team_id)
            const resp = await request.post(`/api/environments/${other.team_id}/query/`, {
                headers: { Authorization: `Bearer ${other.personal_api_key}` },
                data: {
                    refresh: 'force_blocking',
                    query: {
                        kind: 'HogQLQuery',
                        query: `SELECT count() FROM events WHERE event = '${eventName}'`,
                    },
                },
            })
            expect(resp.ok(), `other-tenant query failed: ${resp.status()}`).toBe(true)
            // Missing/malformed HogQL results must not be mistaken for zero visible events.
            const count = parseHogQLCount(await resp.json())
            expect(count).toBe(0)
        })
    })
})
