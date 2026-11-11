import assert from 'node:assert/strict'
import test from 'node:test'

import { getTrustedFlindAppMatches } from './flind-toolbar-trusted-hosts.mjs'

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
