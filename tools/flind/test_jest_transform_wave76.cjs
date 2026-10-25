'use strict'
const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const path = require('node:path')

const ROOT = path.resolve(__dirname, '../..')
const FRONTEND = path.join(ROOT, 'frontend')
const t = require(path.join(FRONTEND, 'jest.sucraseTransform.cjs'))
const paths = [
    'src/lib/flindPublicLinks.ts',
    'src/lib/flindSupportMailto.ts',
    'src/lib/flindRegionHosts.ts',
    'src/lib/oauth/oauthClient.ts',
    'src/lib/components/HelpMenu/incidentStatus.ts',
    'src/scenes/authentication/shared/arrivedFromWebsiteLogic.ts',
]

test('six actual browser config modules no longer expose import.meta.env to Jest CJS', () => {
    for (const relative of paths) {
        const filename = path.join(FRONTEND, relative)
        const source = fs.readFileSync(filename, 'utf8')
        assert.match(source, /import\.meta\.env/)
        const modified = t.jestSafeViteEnv(source, filename)
        assert.doesNotMatch(modified, /import\.meta\.env/)
        const output = t.process(source, filename, {})
        assert.doesNotMatch(output.code, /import\.meta\.env/)
    }
})

test('source-level rewrite is syntax aware: literal strings, comments, import.meta.url remain', () => {
    const file = path.join(FRONTEND, 'src/lib/oauth/oauthClient.ts')
    const original =
        'const a=import.meta.env?.VITE_FLIND_OAUTH_US_CLIENT_ID;const b="import.meta.env";const c=import.meta.url;// import.meta.env\n'
    const output = t.jestSafeViteEnv(original, file)
    assert.match(output, /const a=\(\{\}\)\?\.VITE_FLIND_OAUTH_US_CLIENT_ID/)
    assert.match(output, /const b="import.meta.env"/)
    assert.match(output, /const c=import.meta.url/)
    assert.match(output, /\/\/ import.meta.env/)
})

test('SDK instruction snippets and unrelated modules are not rewritten', () => {
    const value = 'const x=import.meta.env.VITE_FLIND_OAUTH_US_CLIENT_ID'
    const snippet = path.join(FRONTEND, 'src/scenes/onboarding/sdks/sdk-install-instructions/react.tsx')
    assert.equal(t.jestSafeViteEnv(value, snippet), value)
    assert.equal(t.jestSafeViteEnv(value, '/unrelated/frontend/src/lib/oauth/oauthOther.ts'), value)
})

test('Jest and dependency extractor use the same transform', () => {
    const config = fs.readFileSync(path.join(FRONTEND, 'jest.config.ts'), 'utf8')
    const extractor = fs.readFileSync(path.join(FRONTEND, 'jest.dependencyExtractor.js'), 'utf8')
    assert.match(config, /<rootDir>\/jest\.sucraseTransform\.cjs/)
    assert.match(extractor, /flindJestTransform\.process/)
    assert.doesNotMatch(extractor, /sucraseJest\.process/)
})

test('built frontend style inputs use only Flind Quill paths', () => {
    for (const rel of [
        'frontend/src/styles/global.scss',
        'products/tasks/frontend/infrastructure/infrastructureAdmin.css',
    ]) {
        const source = fs.readFileSync(path.join(ROOT, rel), 'utf8')
        assert.doesNotMatch(source, /@posthog\/quill\/dist/)
        assert.match(source, /@flind\/quill\/dist/)
    }
    const q = require(path.join(ROOT, 'packages/quill/package.json'))
    assert.match(q.scripts.build, /@flind\/quill-\*/)
    assert.doesNotMatch(q.scripts.build, /@posthog\/quill-/)
})

test('product flows only use explicitly registered regions and same-origin images', () => {
    const uses = [
        'products/conversations/frontend/components/Chat/aiDraftAction.ts',
        'products/signals/frontend/inbox/components/signalCards/ConversationsTicketSignalCard.tsx',
    ]
    for (const file of uses) {
        const source = fs.readFileSync(path.join(ROOT, file), 'utf8')
        assert.match(source, /isTrustedFlindUrl/)
        assert.doesNotMatch(source, /isTrustedPostHogUrl/)
    }
    for (const file of [
        'products/customer_analytics/frontend/components/Accounts/accountRelatedUserAdminUrl.ts',
        'products/conversations/frontend/scenes/ticket/supportTicketSceneLogic.ts',
    ]) {
        const source = fs.readFileSync(path.join(ROOT, file), 'utf8')
        assert.match(source, /flindRegionHost/)
        assert.doesNotMatch(source, /CLOUD_HOSTNAMES/)
    }
})
