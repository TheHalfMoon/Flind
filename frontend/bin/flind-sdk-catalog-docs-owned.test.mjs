import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const at = (relative) => readFileSync(new URL('../src/scenes/onboarding/sdks/' + relative, import.meta.url), 'utf8')
const catalog = at('allSDKs.tsx')
const selector = at('getAvailableSDKs.ts')
const snippet = at('SDKSnippet.tsx')
const error = at('error-tracking/ErrorTrackingSDKInstructions.tsx')
const replay = at('session-replay/SessionReplaySDKInstructions.tsx')
const docsHelper = readFileSync(new URL('../src/lib/flindPublicLinks.ts', import.meta.url), 'utf8')

test('all 93 SDK catalog documentation destinations derive from Flind-owned HTTPS docs or are absent', () => {
    const count = (catalog.match(/docsLink: flindDocsUrl\('/g) ?? []).length
    assert.equal(count, 93)
    assert.match(catalog, /import \{ flindDocsUrl \} from 'lib\/flindPublicLinks'/)
    assert.doesNotMatch(catalog, /docsLink:\s*['"]https?:\/\//)
    assert.doesNotMatch(catalog, /posthog\.com\/docs\//)
    assert.match(catalog, /docsLink: flindDocsUrl\('libraries\/node'\) \?\? ''/)
    assert.match(catalog, /docsLink: flindDocsUrl\('libraries\/react-native'\) \?\? ''/)
})

test('an absent Flind docs root renders guidance instead of a dead or donor navigation link', () => {
    assert.match(snippet, /\{sdk\.docsLink \? \(/)
    assert.match(snippet, /SDK documentation is not configured for this Flind instance/)
    assert.match(snippet, /Read the Flind SDK documentation/)
    assert.match(docsHelper, /export function flindDocsUrl/)
    assert.match(docsHelper, /url\.protocol !== 'https:'/)
})

test('feature-specific SDK docs overrides are first-party and cannot introduce a donor destination', () => {
    for (const [name, source] of [['Error tracking', error], ['Session replay', replay]]) {
        assert.match(source, /flindDocsUrl\('/, name)
        assert.doesNotMatch(source, /https?:\/\/(?:app\.)?posthog\.(?:com|dev)/, name)
    }
    assert.match(selector, /isOwnedFlindDocsDestination\(rawDocsOverride\)/)
    assert.match(selector, /\? rawDocsOverride : ''/)
    assert.match(selector, /rawDocsOverride !== undefined/)
})
