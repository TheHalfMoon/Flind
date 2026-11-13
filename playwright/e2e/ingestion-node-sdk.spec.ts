import { PostHog } from '@flind/node'
import { randomString } from '../utils'
import { assertForeignPersonalKeyCannotQueryTeam } from '../utils/assert-foreign-team-query-denied'
import { parseHogQLCount } from '../utils/parse-hogql-count'
import { expect, test } from '../utils/workspace-test-base'

// Only run with explicit ingestion=true CI opt-in. The generic browser and
// direct-event checks use the dev proxy, but the Node SDK cannot use an HTTP
// hostname like localhost: SDK policy permits only numeric loopback. Connect
// directly to the already health-checked local Rust capture port instead.
const PROXY_BASE_URL = process.env.E2E_PROXY_URL || 'http://localhost:8010'
const LOCAL_CAPTURE_ORIGIN = 'http://127.0.0.1:3307'

test.describe('Flind Node SDK ingestion', () => {
    test('Node SDK event reaches ClickHouse but not another organization', async ({ request, playwrightSetup }) => {
        test.setTimeout(180_000)
        const host = new URL(PROXY_BASE_URL)
        expect(host.protocol).toBe('http:')
        expect(['localhost', '127.0.0.1']).toContain(host.hostname)
        expect(host.username).toBe('')
        expect(host.password).toBe('')
        expect(host.search).toBe('')
        expect(host.hash).toBe('')
        expect(host.pathname).toBe('/')
        // SDK host policy only permits HTTP on numeric loopback. Verify the
        // dev proxy's local origin, but send this Node test to the separately
        // health-checked Rust capture service on port 3307 instead.
        host.hostname = '127.0.0.1'
        expect(host.origin).toBe('http://127.0.0.1:8010')
        const captureResponses: number[] = []
        const captureErrors: string[] = []

        const workspace = await playwrightSetup.createWorkspace({ skip_onboarding: true, no_demo_data: true })
        const authHeaders = { Authorization: 'Bearer ' + workspace.personal_api_key }
        const eventName = randomString('flind_node_sdk_e2e_')
        const team = await request.get('/api/environments/' + workspace.team_id + '/', { headers: authHeaders })
        expect(team.ok()).toBe(true)
        const apiToken: unknown = (await team.json()).api_token
        expect(typeof apiToken).toBe('string')
        expect((apiToken as string).length).toBeGreaterThan(0)

        await test.step('send event through the real Node SDK on loopback', async () => {
            const sdk = new PostHog(apiToken as string, {
                host: LOCAL_CAPTURE_ORIGIN,
                fetch: async (url, options) => {
                    const target = new URL(url)
                    // No server tokens or payloads are logged, and a regression to
                    // an external endpoint fails before sending any credentials.
                    expect(target.origin).toBe(LOCAL_CAPTURE_ORIGIN)
                    expect(target.pathname).toBe('/batch/')
                    const response = await fetch(url, options)
                    captureResponses.push(response.status)
                    return response
                },
                flushAt: 1,
                flushInterval: 0,
                maxRetries: 0,
                requestTimeout: 10000,
                enableExceptionAutocapture: false,
            })
            sdk.on('error', (error) => captureErrors.push(error instanceof Error ? error.name : 'sdk_error'))
            try {
                sdk.capture({
                    distinctId: randomString('flind-node-synthetic-'),
                    event: eventName,
                    properties: { flind_node_ingestion_test: true },
                })
                await sdk.flush()
            } finally {
                await sdk.shutdown()
            }
            // Diagnostics print only HTTP status codes and error classes, not
            // URL credentials, request bodies, tokens, or tenant identifiers.
            console.info('Flind Node SDK capture HTTP status:', captureResponses.join(',') || 'none')
            console.info('Flind Node SDK error classes:', captureErrors.join(',') || 'none')
            expect(captureResponses.length, 'Node SDK must issue an HTTP batch request').toBeGreaterThan(0)
            expect(captureResponses.every((status) => status >= 200 && status < 300), 'Rust capture must accept SDK batch').toBe(true)
            expect(captureErrors, 'Node SDK must not silently swallow delivery errors').toEqual([])
        })

        const queryCount = async (teamId: number, token: string): Promise<number> => {
            const resp = await request.post('/api/environments/' + teamId + '/query/', {
                headers: { Authorization: 'Bearer ' + token },
                data: {
                    refresh: 'force_blocking',
                    query: {
                        kind: 'HogQLQuery',
                        query: "SELECT count() FROM events WHERE event = '" + eventName + "'",
                    },
                },
            })
            if (!resp.ok()) {
                throw new Error('Node SDK ingestion query returned HTTP ' + resp.status())
            }
            return parseHogQLCount(await resp.json())
        }

        await test.step('event is persisted and queryable in originating team', async () => {
            await expect.poll(
                () => queryCount(workspace.team_id, workspace.personal_api_key),
                { timeout: 90000, intervals: [2000, 5000] }
            ).toBeGreaterThan(0)
        })

        await test.step('another organization has exactly zero matching events', async () => {
            const other = await playwrightSetup.createWorkspace({ skip_onboarding: true, no_demo_data: true })
            expect(other.team_id).not.toBe(workspace.team_id)
            expect(other.organization_id).not.toBe(workspace.organization_id)
            expect(other.user_id).not.toBe(workspace.user_id)
            const count = await queryCount(other.team_id, other.personal_api_key)
            expect(count).toBe(0)
            await assertForeignPersonalKeyCannotQueryTeam(request, workspace.team_id, other.personal_api_key, eventName)
            await assertForeignPersonalKeyCannotQueryTeam(request, other.team_id, workspace.personal_api_key, eventName)
        })
    })
})
