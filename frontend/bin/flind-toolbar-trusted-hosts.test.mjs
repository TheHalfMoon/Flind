import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

import { getFlindExternalConnectable, getTrustedFlindAppMatches } from './flind-toolbar-trusted-hosts.mjs'

test('no inherited host permissions by default', () => {
    assert.deepEqual(getTrustedFlindAppMatches(''), [])
    assert.deepEqual(getTrustedFlindAppMatches('   '), [])
})
test('explicit customer-owned HTTPS hosts are deterministic and deduplicated', () => {
    assert.deepEqual(
        getTrustedFlindAppMatches('https://z.example.com, https://a.example.com/,https://z.example.com'),
        ['https://a.example.com/*', 'https://z.example.com/*']
    )
})
test('local development is opt-in only', () => {
    assert.deepEqual(getTrustedFlindAppMatches('http://localhost'), ['http://localhost/*'])
})
test('rejects insecure or overly broad host patterns and inherited upstream hosts', () => {
    for (const origin of [
        'http://example.com', 'https://*.example.com', 'https://example.com:8443',
        'https://example.com/path', 'https://example.com/?token=x', 'https://user@example.com',
        'https://app.posthog.com', 'https://posthog.com', 'https://evil.example.com,',
        'https://example.com#fragment', 'https://example.com, ,https://other.example.com'
    ]) {
        assert.throws(() => getTrustedFlindAppMatches(origin), undefined, origin)
    }
})

test('manifest fragment is absent by default and only contains approved origins', () => {
    assert.deepEqual(getFlindExternalConnectable(''), {})
    assert.deepEqual(
        getFlindExternalConnectable('https://flind.example.org'),
        { externally_connectable: { matches: ['https://flind.example.org/*'] } }
    )
    assert.throws(() => getFlindExternalConnectable('https://app.posthog.com'))
})

test('toolbar extension manifest actually uses the opt-in host policy', () => {
    // A helper-only test would miss a regression that hardcodes upstream
    // origins directly in the real generated Chrome manifest.
    const toolbarSource = readFileSync(new URL('../toolbar-config.mjs', import.meta.url), 'utf8')
    const manifestStart = toolbarSource.indexOf('function buildToolbarExtensionManifest()')
    const manifestEnd = toolbarSource.indexOf('export function finalizeToolbarExtensionBuild', manifestStart)
    assert.ok(manifestStart >= 0 && manifestEnd > manifestStart, 'toolbar extension manifest builder must exist')
    assert.match(toolbarSource, /import \{ getFlindExternalConnectable \} from '\.\/bin\/flind-toolbar-trusted-hosts\.mjs'/)
    const manifestSource = toolbarSource.slice(manifestStart, manifestEnd)
    assert.match(manifestSource, /\.\.\.getFlindExternalConnectable\(\)/)
    assert.doesNotMatch(manifestSource, /(?:us|eu|app)\.posthog\.com/)
})
