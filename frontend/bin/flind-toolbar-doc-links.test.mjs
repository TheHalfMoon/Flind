import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const sources = [
    '../src/toolbar/extension/components/more/ExtensionMoreMenu.tsx',
    '../src/toolbar/extension/components/web-vitals/ExtensionWebVitalsMenu.tsx',
    '../src/toolbar/shared/elements/SelectorQualityWarning.tsx',
]

test('Flind toolbar menus do not send users to inherited vendor documentation', () => {
    for (const path of sources) {
        const content = readFileSync(new URL(path, import.meta.url), 'utf8')
        assert.ok(!content.includes('posthog.com/docs'), path)
    }
})

test('toolbar retains working functionality and local guidance', () => {
    const more = readFileSync(new URL(sources[0], import.meta.url), 'utf8')
    const vitals = readFileSync(new URL(sources[1], import.meta.url), 'utf8')
    const selector = readFileSync(new URL(sources[2], import.meta.url), 'utf8')
    for (const feature of ['ExtensionDebugInfo', 'ExtensionPiiMasking', 'ExtensionScreenshotForEvent']) {
        assert.ok(more.includes('<' + feature + ' />'), feature)
    }
    assert.ok(vitals.includes('View all metrics'))
    assert.ok(vitals.includes('reload-web-vitals'))
    assert.ok(selector.includes('data-analytics'))
    assert.ok(selector.includes('Fragile selector:'))
})
