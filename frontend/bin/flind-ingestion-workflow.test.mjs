import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const workflow = readFileSync(new URL('../../.github/workflows/flind-e2e.yml', import.meta.url), 'utf8')
const spec = readFileSync(new URL('../../playwright/e2e/ingestion-capture.spec.ts', import.meta.url), 'utf8')

test('expensive ingestion journey is opt-in, not part of normal Flind E2E', () => {
    assert.match(workflow, /workflow_dispatch:\s+inputs:\s+ingestion:/)
    assert.match(workflow, /type: boolean\s+default: false/)
    assert.match(workflow, /FLIND_INGESTION_SMOKE:/)
    assert.match(workflow, /- name: Run Flind journeys/)
    const conditionalSteps = workflow.match(/if: env\.FLIND_INGESTION_SMOKE == 'true'/g) ?? []
    assert.equal(conditionalSteps.length, 2)
})

test('capture and ingestion use real services with test databases', () => {
    assert.match(workflow, /up -d --wait --wait-timeout 300 proxy capture ingestion-general/)
    assert.match(workflow, /POSTHOG_DB_NAME: posthog_e2e_test/)
    assert.match(workflow, /POSTHOG_PERSONS_DB_NAME: posthog_persons_e2e_test/)
    assert.match(workflow, /E2E_PROXY_URL: http:\/\/localhost:8010/)
    assert.match(workflow, /playwright test e2e\/ingestion-capture\.spec\.ts/)
    assert.match(workflow, /COMPOSE_PROFILES: capture,ingestion/)
    assert.match(workflow, /Capture and ingestion service logs on failure/)
})

test('real ingestion test verifies capture response and queryable event', () => {
    assert.match(spec, /request\.post\(`\$\{PROXY_BASE_URL\}\/e\/`/)
    assert.match(spec, /expect\(captured\.ok\(\)\)\.toBe\(true\)/)
    assert.match(spec, /refresh: 'force_blocking'/)
    assert.match(spec, /kind: 'HogQLQuery'/)
    assert.match(spec, /SELECT count\(\) FROM events/)
    assert.match(spec, /\.toBeGreaterThan\(0\)/)
})
