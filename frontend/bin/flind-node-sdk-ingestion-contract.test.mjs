import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const spec = readFileSync(new URL('../../playwright/e2e/ingestion-node-sdk.spec.ts', import.meta.url), 'utf8')
const workflow = readFileSync(new URL('../../.github/workflows/flind-e2e.yml', import.meta.url), 'utf8')
const pkg = JSON.parse(readFileSync(new URL('../../playwright/package.json', import.meta.url), 'utf8'))
const lock = readFileSync(new URL('../../pnpm-lock.yaml', import.meta.url), 'utf8')

test('real Node SDK is installed from Flind workspace, not a donor remote package', () => {
    assert.equal(pkg.dependencies['@flind/node'], 'workspace:*')
    assert.match(lock, /playwright:[\s\S]*?'@flind\/node':\s*\n\s*specifier: workspace:\*/)
    assert.match(spec, /import \{ PostHog \} from '@flind\/node'/)
    assert.match(spec, /new PostHog\(apiToken as string/)
    assert.match(spec, /await sdk\.flush\(\)/)
    assert.match(spec, /await sdk\.shutdown\(\)/)
})

test('opt-in ingestion executes Node SDK end-to-end alongside capture and browser SDK', () => {
    assert.match(workflow, /if: env\.FLIND_INGESTION_SMOKE == 'true'/)
    assert.match(workflow, /ingestion-node-sdk\.spec\.ts/)
    assert.match(spec, /expect\(\['localhost', '127\.0\.0\.1'\]\)\.toContain\(host\.hostname\)/)
})

test('positive ClickHouse proof precedes strict cross-tenant negative control', () => {
    const yes = spec.indexOf('event is persisted and queryable in originating team')
    const no = spec.indexOf('another organization has exactly zero matching events')
    assert.ok(yes > 0 && no > yes)
    assert.match(spec, /refresh: 'force_blocking'/)
    assert.match(spec, /parseHogQLCount\(await resp\.json\(\)\)/)
    assert.match(spec, /other\.team_id\)\.not\.toBe\(workspace\.team_id\)/)
    assert.match(spec, /expect\(count\)\.toBe\(0\)/)
})
