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
        assert.doesNotMatch(content, /https?:\\/\\/(?:www\\.)?posthog\\.com\\/docs(?:\\/|\\?|#|['"])/i, path)
    }
})
test('toolbar retains working functionality and local guidance', () => {
    const more = readFileSync(new URL(sources[0], import.meta.url), 'utf8')
    const vitals = readFileSync(new URL(sources[1], import.meta.url), 'utf8')
    const selector = readFileSync(new URL(sources[2], import.meta.url), 'utf8')
    for (const feature of ['ExtensionDebugInfo', 'ExtensionPiiMasking', 'ExtensionScreenshotForEvent']) {
        assert.match(more, new RegExp('<' + feature + '\\s*\\/>'))
    }
    assert.match(vitals, /View all metrics/)
    assert.match(vitals, /reload-web-vitals/)
    assert.match(selector, /data-analytics/)
    assert.match(selector, /Fragile selector:/)
})
