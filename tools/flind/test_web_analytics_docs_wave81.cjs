'use strict'
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { test } = require('node:test')
const ts = require('../../frontend/node_modules/typescript')

const ROOT = path.resolve(__dirname, '../..')
const files = [
    'frontend/src/scenes/web-analytics/health/webAnalyticsHealthLogic.ts',
    'frontend/src/scenes/web-analytics/PagePerformance.tsx',
    'frontend/src/scenes/web-analytics/PagePerformanceBreakdownModal.tsx',
    'frontend/src/scenes/web-analytics/WebAnalyticsFilters.tsx',
    'frontend/src/scenes/web-analytics/tiles/WebAnalyticsRecordings.tsx',
]
const source = (file) => fs.readFileSync(path.join(ROOT, file), 'utf8')

test('five active Web Analytics views contain no hardcoded upstream docs URLs', () => {
    for (const file of files) {
        assert.doesNotMatch(source(file), /https?:\/\/(?:www\.)?posthog\.com\/docs(?:\/|#|['"])/, file)
        assert.match(source(file), /flindDocs(?:Section)?Url\(/, file)
    }
})

test('every changed Web Analytics module parses with pinned TypeScript', () => {
    for (const file of files) {
        const kind = file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
        const ast = ts.createSourceFile(file, source(file), ts.ScriptTarget.Latest, true, kind)
        assert.deepEqual(
            ast.parseDiagnostics.map((x) => x.messageText),
            [],
            file
        )
    }
})

test('health check actions have no unowned external installation URL fallback', () => {
    const logic = source(files[0])
    assert.match(logic, /INSTALL_GUIDE_ACTION: HealthCheckAction \| undefined/)
    assert.match(logic, /COMPLETE_INSTALL_ACTION: HealthCheckAction \| undefined/)
    assert.match(logic, /failingAction: SESSION_ID_DOCS/)
    assert.match(logic, /docsUrl: SESSION_ID_DOCS \?\? undefined/)
    assert.match(logic, /urls\.settings\('environment-web-analytics'\)/)
    assert.doesNotMatch(logic, /Complete the PostHog installation/)
})

test('page performance never creates inert external doc buttons', () => {
    const page = source(files[1])
    const modal = source(files[2])
    assert.match(page, /SERVER_LOGS_DOCS \?/)
    assert.match(page, /FlindDocsLink path="data\/channel-type"/)
    assert.match(modal, /\{GSC_DOCS_URL && \(/)
    assert.doesNotMatch(page, /How PostHog works out where/)
    assert.doesNotMatch(modal, /https:\/\/posthog\.com\/docs/)
})

test('unconfigured recordings docs do not leave a clickable but empty button', () => {
    const recordings = source(files[4])
    assert.match(recordings, /buttonText: RECORDINGS_DOCS_URL \? 'Learn more' : undefined/)
    assert.match(recordings, /buttonTo: RECORDINGS_DOCS_URL \?\? undefined/)
    assert.doesNotMatch(recordings, /buttonText: 'Learn more',\s*buttonTo: undefined/)
})

test('live user count help cannot fall back to upstream', () => {
    assert.match(source(files[3]), /flindDocsSectionUrl\(\s*'web-analytics\/faq'/)
    assert.match(source(files[3]), /\?\? undefined/)
})
