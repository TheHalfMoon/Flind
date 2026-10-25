'use strict'
const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('../../frontend/node_modules/typescript')

const ROOT = path.resolve(__dirname, '../..')
const docsSurfaces = [
    'products/conversations/frontend/emptyState/supportEmptyState.tsx',
    'products/conversations/frontend/components/IdentityBadge/IdentityBadge.tsx',
    'products/conversations/frontend/components/ConversationsDisabledBanner/ConversationsDisabledBanner.tsx',
    'products/customer_analytics/frontend/emptyState/customerAnalyticsEmptyState.tsx',
    'products/customer_analytics/frontend/featurePreviewGate.ts',
    'products/signals/frontend/inbox/components/InboxMcpBanner.tsx',
    'products/signals/frontend/inbox/components/config/agentRosterMeta.ts',
    'products/signals/frontend/inbox/components/config/scouts/ScoutHelperSkillLinks.tsx',
    'products/signals/frontend/inbox/components/onboarding/InboxActivationPanel.tsx',
    'products/signals/frontend/inbox/components/onboarding/InboxReportPreview.tsx',
    'products/signals/frontend/inbox/components/onboarding/InboxSetupEmptyState.tsx',
    'products/signals/frontend/inbox/components/onboarding/InboxSetupScoutsStep.tsx',
]
const additionalSurfaces = ['products/conversations/frontend/scenes/myTickets/MyTicketsScene.tsx']

test('each migrated product documentation surface uses the Flind-owned URL gate', () => {
    for (const relative of docsSurfaces) {
        const source = fs.readFileSync(path.join(ROOT, relative), 'utf8')
        assert.match(source, /flindDocsUrl\(/, relative)
        assert.doesNotMatch(source, /https?:\/\/(?:www\.)?posthog\.com\/docs/, relative)
    }
})

test('no donor-host community or helper skill links survive in active migrated scenes', () => {
    const sources = [...docsSurfaces, ...additionalSurfaces].map((p) => fs.readFileSync(path.join(ROOT, p), 'utf8'))
    for (const source of sources) {
        assert.doesNotMatch(source, /https:\/\/posthog\.com\/questions/)
        assert.doesNotMatch(source, /github\.com\/PostHog\/ai-plugin/)
        assert.doesNotMatch(source, /https?:\/\/posthog\.com\/docs/)
    }
    const ticketScene = fs.readFileSync(path.join(ROOT, additionalSurfaces[0]), 'utf8')
    assert.match(ticketScene, /flindPublicUrl\('community'\)/)
    assert.match(ticketScene, /Ask your instance administrator for help/)
})

test('preserves backend stable agent group key but replaces visible legacy group label', () => {
    const roster = fs.readFileSync(
        path.join(ROOT, 'products/signals/frontend/inbox/components/config/agentRosterMeta.ts'),
        'utf8'
    )
    assert.match(roster, /id: 'posthog'/)
    assert.match(roster, /label: 'Flind data'/)
    assert.doesNotMatch(roster, /label: 'PostHog data'/)
})

test('all affected TypeScript and TSX modules parse with the pinned TypeScript compiler', () => {
    for (const rel of ['frontend/src/lib/flindPublicLinks.ts', ...docsSurfaces, ...additionalSurfaces]) {
        const source = fs.readFileSync(path.join(ROOT, rel), 'utf8')
        const tree = ts.createSourceFile(
            rel,
            source,
            ts.ScriptTarget.Latest,
            true,
            rel.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
        )
        assert.deepEqual(
            tree.parseDiagnostics.map((problem) => problem.messageText),
            [],
            rel
        )
    }
})

test('external help controls fail closed when the operator leaves docs unconfigured', () => {
    const banner = fs.readFileSync(
        path.join(
            ROOT,
            'products/conversations/frontend/components/ConversationsDisabledBanner/ConversationsDisabledBanner.tsx'
        ),
        'utf8'
    )
    const mcp = fs.readFileSync(
        path.join(ROOT, 'products/signals/frontend/inbox/components/InboxMcpBanner.tsx'),
        'utf8'
    )
    const empty = fs.readFileSync(
        path.join(ROOT, 'products/customer_analytics/frontend/emptyState/customerAnalyticsEmptyState.tsx'),
        'utf8'
    )
    assert.match(banner, /\{docsUrl && \(/)
    assert.match(mcp, /mcpDocs\s*\?/)
    assert.match(empty, /primaryAction: groupAnalyticsDocs/)
    assert.match(empty, /:\s*undefined/)
})
