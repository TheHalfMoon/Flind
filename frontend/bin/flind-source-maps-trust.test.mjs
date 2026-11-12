import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import test from 'node:test'

const base = new URL('../../products/error_tracking/', import.meta.url)
const read = (path) => readFileSync(new URL(path, base), 'utf8')
const banner = 'frontend/scenes/ErrorTrackingScene/banners/'

test('Source Maps UI retains diagnostics without external upload wizards', () => {
    const source = read(banner + 'SourceMapsBanner.tsx')
    const examples = read(banner + 'SourceMapsExamplesModal.tsx')
    const browser = read(banner + 'SourceMapsExamplesBrowser.tsx')
    assert.match(source, /label: 'See missing frames'/)
    assert.match(source, /openExamples\(platform\)/)
    assert.match(source, /SourceMapsExamplesModal/)
    assert.match(examples, /<SourceMapsExamplesBrowser/)
    assert.match(examples, /onClick={closeExamples}/)
    assert.match(browser, /sourceMapsPlatforms/)
    for (const [name, content] of [['banner', source], ['examples', examples]]) {
        assert.doesNotMatch(content, /@posthog\/wizard|posthog\.com\/docs|Fix with Wizard/i, name)
    }
})

test('obsolete source-map upload wizard cannot be rendered or copied', () => {
    for (const file of ['SourceMapsFixModal.tsx', 'sourceMapsFixWizardLogic.ts', 'sourceMapsWizardVisuals.tsx']) {
        assert.equal(existsSync(new URL(banner + file, base)), false, file)
    }
    const platforms = read(banner + 'sourceMapsPlatforms.ts')
    for (const key of ['javascript:', 'java:', 'native:']) {
        assert.ok(platforms.includes(key), key)
    }
})

test('health and digest reporting never promote a provider CLI or off-instance docs URL', () => {
    const digest = read('backend/weekly_digest.py')
    const contracts = read('backend/facade/contracts.py')
    const health = read('backend/temporal/health_checks/missing_source_maps.py')
    const testSource = read('backend/test/test_weekly_digest.py')
    for (const source of [digest, contracts, health]) {
        assert.doesNotMatch(source, /@posthog\/wizard|posthog\.com\/docs\/error-tracking\/upload-source-maps/)
    }
    assert.match(digest, /"wizard_command": None/)
    assert.match(digest, /"docs_url": None/)
    assert.match(digest, /Flind administrator/)
    assert.match(health, /approved instance-specific upload method/)
    assert.match(contracts, /SOURCE_MAPS_DOCS_URL: str \| None = None/)
    assert.match(testSource, /result\["wizard_command"\] is None/)
    assert.match(testSource, /result\["docs_url"\] is None/)
})
