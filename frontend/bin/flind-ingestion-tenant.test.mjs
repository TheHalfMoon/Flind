import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const spec = readFileSync(new URL('../../playwright/e2e/ingestion-capture.spec.ts', import.meta.url), 'utf8')

test('a real captured event is queried before asserting another tenant sees none', () => {
    const capture = spec.indexOf("await test.step('send an event through the capture endpoint'")
    const confirmed = spec.indexOf("await test.step('poll until the event has been ingested and is queryable'")
    const denied = spec.indexOf("await test.step('another organization cannot query the captured event'")
    assert.ok(capture > -1 && confirmed > capture && denied > confirmed)
    assert.match(spec.slice(confirmed, denied), /\.toBeGreaterThan\(0\)/)
})

test('negative control uses an independent organization and scoped HogQL query', () => {
    const denied = spec.slice(spec.indexOf("await test.step('another organization cannot query the captured event'"))
    assert.match(denied, /const other = await playwrightSetup\.createWorkspace/)
    assert.match(denied, /expect\(other\.team_id\)\.not\.toBe\(workspace\.team_id\)/)
    assert.match(denied, /`\/api\/environments\/\$\{other\.team_id\}\/query\/`/)
    assert.match(denied, /Bearer \$\{other\.personal_api_key\}/)
    assert.match(denied, /refresh: 'force_blocking'/)
    assert.match(denied, /SELECT count\(\) FROM events WHERE event/)
    assert.match(denied, /expect\(Number\(body\.results\?\.\[0\]\?\.\[0\] \?\? 0\)\)\.toBe\(0\)/)
})
