import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../../products/mobile/src/auth/oauth.ts', import.meta.url), 'utf8')
const tests = readFileSync(new URL('../../products/mobile/src/auth/tokenRefresh.test.ts', import.meta.url), 'utf8')
test('OAuth token and revocation clients refuse redirects', () => {
    assert.match(source, /fetch\(url, \{ \.\.\.init, signal: controller\.signal, redirect: 'error' \}\)/)
    assert.match(source, /redirect: 'error',/)
    assert.match(source, /response\.status >= 300 && response\.status < 400/)
    assert.match(tests, /token exchanges explicitly reject cross-origin redirects/)
    assert.match(tests, /token revocation rejects redirects/)
})
