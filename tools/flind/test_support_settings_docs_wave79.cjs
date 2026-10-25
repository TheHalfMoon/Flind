'use strict'
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { test } = require('node:test')
const ts = require('../../frontend/node_modules/typescript')

const ROOT = path.resolve(__dirname, '../..')
const scenes = ['ApiSection', 'TeamsSection', 'SlackSection', 'WidgetSection', 'NotificationsSection', 'GeneralSection']
const docRefs = {
    ApiSection: 1,
    TeamsSection: 2,
    SlackSection: 1,
    WidgetSection: 2,
    NotificationsSection: 1,
    GeneralSection: 2,
}

test('nine first-party Support settings documentation controls have no inherited provider URL', () => {
    let total = 0
    for (const scene of scenes) {
        const relative = 'products/conversations/frontend/scenes/settings/' + scene + '.tsx'
        const source = fs.readFileSync(path.join(ROOT, relative), 'utf8')
        assert.doesNotMatch(source, /https?:\/\/posthog\.com\/docs/, scene)
        assert.match(source, /FlindDocsLink/, scene)
        const controls = source.match(/<FlindDocsLink\b/g) ?? []
        assert.equal(controls.length, docRefs[scene], scene)
        total += controls.length
    }
    assert.equal(total, 9)
})

test('existing public SDK and integration identifiers are not blindly renamed', () => {
    const api = fs.readFileSync(
        path.join(ROOT, 'products/conversations/frontend/scenes/settings/ApiSection.tsx'),
        'utf8'
    )
    const slack = fs.readFileSync(
        path.join(ROOT, 'products/conversations/frontend/scenes/settings/SlackSection.tsx'),
        'utf8'
    )
    assert.match(api, /posthog\.conversations/)
    assert.match(slack, /SupportHog/)
})

test('both first-party docs helpers and all six Support settings files parse as TypeScript', () => {
    const files = [
        'frontend/src/lib/flindPublicLinks.ts',
        'frontend/src/lib/components/FlindDocsLink/FlindDocsLink.tsx',
        ...scenes.map((scene) => 'products/conversations/frontend/scenes/settings/' + scene + '.tsx'),
    ]
    for (const relative of files) {
        const file = path.join(ROOT, relative)
        const tree = ts.createSourceFile(
            file,
            fs.readFileSync(file, 'utf8'),
            ts.ScriptTarget.Latest,
            true,
            relative.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
        )
        assert.deepEqual(
            tree.parseDiagnostics.map((x) => x.messageText),
            [],
            relative
        )
    }
})
