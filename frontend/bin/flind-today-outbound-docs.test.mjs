import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

// Avoid sending Flind users to donor-operated documentation from the Today surface.
// Re-enable docs links after Flind-owned documentation routes are implemented.
const files = [
    '../src/layout/today/TodayAiPanel.tsx',
    '../src/layout/today/TodayPeopleNavRow.tsx',
    '../src/layout/today/todayPeopleRows.tsx',
]
test('Today panels do not expose inherited vendor documentation links', () => {
    for (const file of files) {
        const source = readFileSync(new URL(file, import.meta.url), 'utf8')
        assert.doesNotMatch(source, /https?:\/\/(?:www\.)?posthog\.com\/docs\b/i, file)
        assert.doesNotMatch(source, /npx\s+@posthog\/wizard/i, file)
    }
})
test('AI unavailable state retains actionable local configuration instructions', () => {
    const source = readFileSync(new URL(files[0], import.meta.url), 'utf8')
    assert.match(source, /ANTHROPIC_API_KEY/)
    assert.match(source, /restart Flind/)
    assert.match(source, /Flind AI isn't set up yet/)
})
