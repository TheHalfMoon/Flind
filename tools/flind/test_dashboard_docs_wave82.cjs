'use strict'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { test } = require('node:test')
const ts = require('../../frontend/node_modules/typescript')

const root = path.resolve(__dirname, '../..')
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8')
const dashboard = 'frontend/src/scenes/web-analytics/webAnalyticsLogic.tsx'
const popover = 'frontend/src/scenes/web-analytics/WebAnalyticsDashboard.tsx'
const model = 'frontend/src/scenes/web-analytics/common.ts'

test('all 20 inherited dashboard documentation references use first-party helpers', () => {
    const source = read(dashboard)
    assert.doesNotMatch(source, /https?:\/\/(?:www\.)?posthog\.com\/docs\//)
    const urls = source.match(/url:\s*flindDocs(?:Section)?Url\(/g) ?? []
    const inline = source.match(/<FlindDocsLink\b/g) ?? []
    assert.equal(urls.length, 18)
    assert.equal(inline.length, 2)
    assert.match(source, /flindDocsSectionUrl\('web-analytics\/dashboard'/)
    assert.match(source, /flindDocsUrl\('session-replay'\)/)
})

test('popover always performs an explicit trusted-docs URL check before creating its external action', () => {
    const source = read(popover)
    assert.match(source, /const ownedDocsUrl = isOwnedFlindDocsDestination\(url\) \? url : undefined/)
    assert.match(source, /\{ownedDocsUrl && \(/)
    assert.match(source, /to=\{ownedDocsUrl\}/)
    assert.doesNotMatch(source, /\{url && \(/)
})

test('dashboard docs model no longer forces upstream-only URL literal type', () => {
    assert.match(read(model), /url\?: string/)
    assert.doesNotMatch(read(model), /PostHogComDocsURL/)
    assert.match(read(popover), /url\?: string/)
    assert.doesNotMatch(read(popover), /PostHogComDocsURL/)
})

test('all affected modules parse with the pinned local TypeScript compiler', () => {
    for (const filename of [dashboard, popover, model, 'frontend/src/lib/flindPublicLinks.ts']) {
        const tree = ts.createSourceFile(
            filename,
            read(filename),
            ts.ScriptTarget.Latest,
            true,
            filename.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
        )
        assert.deepEqual(
            tree.parseDiagnostics.map((x) => x.messageText),
            [],
            filename
        )
    }
})

test('raw dashboard docs admission is separately covered by Jest malicious-URL tests', () => {
    const tests = read('frontend/src/lib/flindPublicLinks.test.ts')
    assert.match(tests, /isOwnedFlindDocsDestination/)
    assert.match(tests, /posthog\.com\/docs/)
    assert.match(tests, /flind\.example\.evil\.com/)
    assert.match(tests, /8443/)
    assert.match(tests, /paths\?redirect=evil/)
})
