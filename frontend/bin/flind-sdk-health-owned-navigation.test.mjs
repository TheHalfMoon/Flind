import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const at = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')
const catalog = at('../src/scenes/onboarding/shared/sdkHealth/sdkConstants.ts')
const component = at('../src/scenes/onboarding/shared/sdkHealth/SdkHealthComponents.tsx')
const scene = at('../src/scenes/onboarding/shared/sdkHealth/SdkHealthScene.tsx')
const healthIssue = at('../src/scenes/health/renderers/SdkOutdatedRenderer.tsx')
const links = at('../src/lib/flindPublicLinks.ts')

test('all 31 historical SDK types survive as typed first-party documentation paths with no vendor release destinations', () => {
    const paths = catalog.match(/const SDK_DOCS_PATHS: Record<SdkType, string> = \{([\s\S]*?)\n\}/)
    assert.ok(paths)
    const types = [...paths[1].matchAll(/^\s{4}(?:'([^']+)'|([a-z]+)): '([^']+)',?$/gm)]
    assert.equal(types.length, 31)
    const keys = types.map((m) => m[1] || m[2])
    assert.equal(new Set(keys).size, 31)
    for (const [, , , path] of types) assert.match(path, /^[a-z0-9][a-z0-9/_-]*$/)
    for (const key of ['web', 'posthog-ios', 'posthog-node', 'posthog-python', 'posthog-react-native', 'posthog-android', 'posthog-kmp', 'posthog-rs', 'posthog-node-mcp', 'posthog-godot', 'posthog-unreal', 'js']) {
        assert.ok(keys.includes(key), 'missing SDK diagnostic type: ' + key)
    }
    assert.doesNotMatch(catalog, /https?:\/\//)
    assert.match(catalog, /flindPublicUrl\('changelog'\)/)
    assert.match(catalog, /flindDocsUrl\(docsPath\)/)
    assert.match(catalog, /releases: string \| null; docs: string \| null/)
})

test('every SDK health navigation surface rejects absent Flind-owned links and shows usable text', () => {
    for (const [name, source] of [['SDK diagnostics',component],['SDK health scene',scene],['Health page issue',healthIssue]]) {
        assert.doesNotMatch(source, /(?:posthog\.com\/docs|github\.com\/PostHog\/)/i, name)
        assert.doesNotMatch(source, /<Link\s+to="https?:\/\//i, name)
    }
    assert.match(component, /\{links\.releases && \(/)
    assert.match(component, /\{links\.docs && \(/)
    assert.match(component, /\{updatingDocs && \(/)
    assert.match(component, /Flind SDK documentation is not configured/)
    assert.match(scene, /updatingDocs \? \(/)
    assert.match(scene, /Flind SDK update guidance is not configured/)
    assert.match(healthIssue, /links\?\.releases \|\| links\?\.docs/)
    assert.match(healthIssue, /\{links\.releases && \(/)
    assert.match(healthIssue, /\{links\.docs && \(/)
    assert.match(healthIssue, /Flind SDK documentation is not configured/)
})

test('deep-link destinations are validated by the same Flind first-party origin guard', () => {
    assert.match(links, /export function flindDocsUrl\(/)
    assert.match(links, /const docsRoot = flindPublicUrl\('docs', hostname, links\)/)
    assert.match(links, /candidate\.origin === owned\.origin/)
    assert.match(links, /url\.protocol !== 'https:'/)
    assert.doesNotMatch(catalog, /releases:\s*['"]https?:\/\//)
    assert.doesNotMatch(catalog, /docs:\s*['"]https?:\/\//)
})
