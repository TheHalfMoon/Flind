import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const files = {
    healthChecks: '../src/scenes/health/components/WebAnalyticsHealthTable.tsx',
    categories: '../src/scenes/health/categoryDetail/categoryDetailConfig.ts',
    recording: '../src/lib/components/ViewRecordingButton/ViewRecordingButton.tsx',
}
const sources = Object.fromEntries(
    Object.entries(files).map(([key, relative]) => [key, readFileSync(new URL(relative, import.meta.url), 'utf8')])
)

test('health and recording diagnostics do not advertise inherited provider documentation', () => {
    for (const [name, source] of Object.entries(sources)) {
        assert.doesNotMatch(source, /https?:\/\/(?:[\w-]+\.)*posthog\.com\b/i, name)
        assert.doesNotMatch(source, /mailto:[\w.+-]+@posthog\.com\b/i, name)
    }
})

test('web analytics health checks preserve local settings and use configured first-party docs only', () => {
    const source = sources.healthChecks
    assert.match(source, /import \{ flindDocsSectionUrl, flindDocsUrl \} from 'lib\/flindPublicLinks'/)
    for (const path of [
        'product-analytics/capture-events', 'web-analytics/scroll-depth',
        'advanced/proxy', 'web-analytics/web-vitals',
    ]) {
        assert.ok(source.includes(`flindDocsUrl('${path}') ?? undefined`), path)
    }
    assert.match(source, /flindDocsSectionUrl\('web-analytics\/dashboard', 'bounce-rate'\) \?\? undefined/)
    assert.match(source, /urls\.settings\('environment-web-analytics', 'web-analytics-authorized-urls'\)/)
    assert.match(source, /urls\.settings\('environment-product-analytics', 'path-cleaning'\)/)
    assert.match(source, /\{meta\?\.docsUrl && \(/)
})

test('health category detail keeps existing internal drill-down routes while docs are optional', () => {
    const source = sources.categories
    assert.match(source, /import \{ flindDocsUrl \} from 'lib\/flindPublicLinks'/)
    for (const path of [
        'data/ingestion-warnings', 'libraries', 'web-analytics',
        'cdp', 'data-warehouse', 'error-tracking',
    ]) {
        assert.ok(source.includes(`flindDocsUrl('${path}') ?? undefined`), path)
    }
    for (const route of ['ingestionWarnings', 'sdkHealth', 'webAnalyticsHealth', 'sources', 'errorTracking']) {
        assert.ok(source.includes(`urls.${route}()`), route)
    }
})

test('recording disabled states retain actionable text and conditionally render owned help', () => {
    const source = sources.recording
    assert.match(source, /import \{ flindDocsSectionUrl \} from 'lib\/flindPublicLinks'/)
    assert.match(source, /flindDocsSectionUrl\('data\/sessions', 'automatically-sending-session-ids'\)/)
    assert.match(source, /flindDocsSectionUrl\('session-replay\/troubleshooting', 'recordings-are-not-being-captured'\)/)
    assert.match(source, /\{sessionDocsUrl \? \(/)
    assert.match(source, /\{replayDocsUrl \? \(/)
    assert.match(source, /Set a session ID on your events to associate them with recordings\./)
    assert.match(source, /Not all recordings are captured\./)
    assert.doesNotMatch(source, /<Link to="https?:\/\//)
})
