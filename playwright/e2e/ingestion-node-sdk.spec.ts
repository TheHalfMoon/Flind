import { PostHog } from '@flind/node'
import { randomString } from '../utils'
import { parseHogQLCount } from '../utils/parse-hogql-count'
import { expect, test } from '../utils/workspace-test-base'

// Only run with the explicit ingestion=true CI opt-in. No external SDK host.
const PROXY_BASE_URL = process.env.E2E_PROXY_URL || 'http://localhost:8010'

test.describe('Flind Node SDK ingestion', () => {
    test('Node SDK event reaches ClickHouse but not another organization', async ({ request, playwrightSetup }) => {
        test.setTimeout(180_000)
        const host = new URL(PROXY_BASE_URL)
        expect(host.protocol).toBe('http:')
        expect(['localhost', '127.0.0.1']).toContain(host.hostname)

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
                host: PROXY_BASE_URL,
                flushAt: 1,
                flushInterval: 0,
                maxRetries: 0,
                requestTimeout: 10000,
                enableExceptionAutocapture: false,
            })
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
            const count = await queryCount(other.team_id, other.personal_api_key)
            expect(count).toBe(0)
        })
    })
})
