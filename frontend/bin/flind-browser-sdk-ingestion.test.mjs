import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const spec = readFileSync(new URL('../../playwright/e2e/ingestion-browser-sdk.spec.ts', import.meta.url), 'utf8')
const workflow = readFileSync(new URL('../../.github/workflows/flind-e2e.yml', import.meta.url), 'utf8')

test('browser SDK smoke uses locally hosted script and explicit instance origin', () => {
    assert.match(spec, /<script src="\/static\/array\.js"><\/script>/)
    assert.match(spec, /api_host: window\.location\.origin/)
    assert.match(spec, /autocapture: false/)
    assert.match(spec, /capture_pageview: false/)
    assert.match(spec, /disable_session_recording: true/)
    assert.match(spec, /sdk\.capture\(name,/)
    assert.match(spec, /SDK capture did not return HTTP 2xx/)
    assert.match(spec, /sdk\.config\.api_host/)
    assert.doesNotMatch(spec, /get_config\(/)
})

test('external browser traffic is blocked, never sent during the smoke', () => {
    assert.match(spec, /await page\.route\('\*\*\/\*'/)
    assert.match(spec, /\['localhost', '127\.0\.0\.1'\]\.includes\(url\.hostname\)/)
    assert.match(spec, /await route\.abort\(\)/)
    assert.match(spec, /externalOrigins\)/)
})

test('browser SDK event must become queryable under local team credentials', () => {
    assert.match(spec, /api\/environments\/\$\{workspace\.team_id\}\/query/)
    assert.match(spec, /refresh: 'force_blocking'/)
    assert.match(spec, /SELECT count\(\) FROM events WHERE event/)
    assert.match(spec, /\.toBeGreaterThan\(0\)/)
    assert.match(workflow, /if: env\.FLIND_INGESTION_SMOKE == 'true'/)
    assert.match(workflow, /ingestion-capture\.spec\.ts e2e\/ingestion-browser-sdk\.spec\.ts/)
})
