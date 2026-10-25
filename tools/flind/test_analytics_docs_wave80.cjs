'use strict'
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { test } = require('node:test')
const ts = require('../../frontend/node_modules/typescript')

const ROOT = path.resolve(__dirname, '../..')
const files = [
    'frontend/src/queries/nodes/WebVitals/WebVitals.tsx',
    'frontend/src/queries/nodes/WebOverview/WebOverview.tsx',
    'frontend/src/queries/nodes/InsightViz/SessionAnalysisWarning.tsx',
    'frontend/src/queries/nodes/InsightViz/EditorFilters.tsx',
    'frontend/src/queries/nodes/HogQLQuery/HogQLQueryEditor.tsx',
    'frontend/src/queries/nodes/InsightViz/TrendsSeries.tsx',
    'frontend/src/queries/nodes/DataTable/renderColumn.tsx',
    'frontend/src/scenes/web-analytics/SessionAttributionExplorer/SessionAttributionExplorerScene.tsx',
]
const read = (relative) => fs.readFileSync(path.join(ROOT, relative), 'utf8')

test('nine migrated analytics controls no longer contain inherited docs URL', () => {
    let references = 0
    for (const file of files) {
        const source = read(file)
        assert.doesNotMatch(source, /https?:\/\/(?:www\.)?posthog\.com\/docs\b/, file)
        const values = source.match(/flindDocs(?:Section)?Url\(|<FlindDocsLink\b/g) ?? []
        assert.ok(values.length > 0, file)
        references += values.length
    }
    assert.equal(references, 9)
})

test('actual JSX typescript compiler parses each migrated analytics surface', () => {
    for (const file of files) {
        const src = read(file)
        const tree = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
        assert.deepEqual(
            tree.parseDiagnostics.map((error) => error.messageText),
            [],
            file
        )
    }
})

test('visible analytics help link renders fail-closed link fallback', () => {
    for (const file of [
        'frontend/src/queries/nodes/WebVitals/WebVitals.tsx',
        'frontend/src/queries/nodes/InsightViz/SessionAnalysisWarning.tsx',
        'frontend/src/queries/nodes/InsightViz/EditorFilters.tsx',
        'frontend/src/queries/nodes/HogQLQuery/HogQLQueryEditor.tsx',
        'frontend/src/scenes/web-analytics/SessionAttributionExplorer/SessionAttributionExplorerScene.tsx',
    ]) {
        assert.match(read(file), /<FlindDocsLink\b/, file)
    }
})

test('analytics props have no implicit provider fallback', () => {
    const typed = [
        'frontend/src/queries/nodes/WebOverview/WebOverview.tsx',
        'frontend/src/queries/nodes/InsightViz/TrendsSeries.tsx',
        'frontend/src/queries/nodes/DataTable/renderColumn.tsx',
        'frontend/src/queries/nodes/InsightViz/EditorFilters.tsx',
    ]
    for (const file of typed) {
        const source = read(file)
        assert.match(source, /flindDocs(?:Section)?Url\(/, file)
        assert.match(source, /\?\? undefined/, file)
    }
})
