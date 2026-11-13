import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const root = new URL('../../playwright/', import.meta.url)
const helper = readFileSync(new URL('utils/assert-foreign-team-query-denied.ts', root), 'utf8')
const specs = [
    ['direct capture', readFileSync(new URL('e2e/ingestion-capture.spec.ts', root), 'utf8')],
    ['Node SDK', readFileSync(new URL('e2e/ingestion-node-sdk.spec.ts', root), 'utf8')],
    ['browser SDK', readFileSync(new URL('e2e/ingestion-browser-sdk.spec.ts', root), 'utf8')],
]
const workflow = readFileSync(new URL('../../.github/workflows/flind-e2e.yml', import.meta.url), 'utf8')

test('authorization probe rejects cross-tenant API access rather than assuming a filtered zero proves auth', () => {
    assert.match(helper, /export async function assertForeignPersonalKeyCannotQueryTeam/)
    assert.match(helper, /\/api\/environments\/\$\{targetTeamId\}\/query\//)
    assert.match(helper, /Authorization: .*foreignPersonalApiKey/)
    assert.match(helper, /expect\(\[401, 403, 404\],/)
    assert.match(helper, /toContain\(response\.status\(\)\)/)
    assert.doesNotMatch(helper, /console\.(?:log|info|warn|error)/)
    assert.doesNotMatch(helper, /response\.json\(\)|response\.text\(\)/)
})

for (const [name, spec] of specs) {
    test(name + ': independent user and both reverse key/team probes follow successful own-team evidence', () => {
        assert.match(spec, /import \{ assertForeignPersonalKeyCannotQueryTeam \}/)
        assert.match(spec, /expect\(other\.team_id\)\.not\.toBe\(workspace\.team_id\)/)
        assert.match(spec, /expect\(other\.organization_id\)\.not\.toBe\(workspace\.organization_id\)/)
        assert.match(spec, /expect\(other\.user_id\)\.not\.toBe\(workspace\.user_id\)/)
        assert.match(spec, /await assertForeignPersonalKeyCannotQueryTeam\(request, workspace\.team_id, other\.personal_api_key, eventName\)/)
        assert.match(spec, /await assertForeignPersonalKeyCannotQueryTeam\(request, other\.team_id, workspace\.personal_api_key, eventName\)/)
        const positive = spec.indexOf('.toBeGreaterThan(0)')
        const negative = spec.indexOf('await assertForeignPersonalKeyCannotQueryTeam')
        assert.ok(positive > 0 && negative > positive, name + ' must prove actual persistence before denial')
        assert.match(spec, /expect\(count\)\.toBe\(0\)|expect\(parseHogQLCount\(await resp\.json\(\)\)\)\.toBe\(0\)/)
    })
}

test('browser SDK positive and negative HogQL checks both reject missing or malformed counts', () => {
    const browser = specs[2][1]
    assert.match(browser, /import \{ parseHogQLCount \} from '\.\.\/utils\/parse-hogql-count'/)
    assert.equal((browser.match(/parseHogQLCount\(await resp\.json\(\)\)/g) ?? []).length, 2)
    assert.doesNotMatch(browser, /Number\(body\.results\?\.\[0\]\?\.\[0\] \?\? 0\)/)
})

test('browser E2E onboarding copy follows fail-closed Flind-owned docs when no host is configured', () => {
    const brand = readFileSync(new URL('e2e/flind-brand-journeys.spec.ts', root), 'utf8')
    assert.match(brand, /SDK documentation is not configured for this Flind instance/)
    assert.match(brand, /Read the Flind SDK documentation/)
    assert.doesNotMatch(brand, /getByText\('Read the SDK documentation'\)/)
})

test('all three actual SDK/capture suites remain behind the opt-in full service E2E journey', () => {
    assert.match(workflow, /workflow_dispatch:\s+inputs:\s+ingestion:/)
    assert.match(workflow, /default: false/)
    assert.match(workflow, /if: env\.FLIND_INGESTION_SMOKE == 'true'/)
    assert.match(workflow, /playwright test e2e\/ingestion-capture\.spec\.ts e2e\/ingestion-browser-sdk\.spec\.ts e2e\/ingestion-node-sdk\.spec\.ts/)
})
