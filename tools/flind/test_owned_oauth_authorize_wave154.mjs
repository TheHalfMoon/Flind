#!/usr/bin/env node
/* Wave154: execute original Flind OAuth authorize logic against in-memory KV. */
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const root = process.env.FLIND_SOURCE_ROOT || process.cwd()
const ref = process.env.FLIND_TEST_REF || 'HEAD'
const tracked = (path) => execFileSync('git', ['-C', root, 'show', ref + ':' + path], {
    encoding: 'utf8', timeout: 45000, maxBuffer: 2_000_000,
})
const temp = mkdtempSync(join(tmpdir(), 'flind-oauth-authorization-'))
const originalFetch = globalThis.fetch
try {
    globalThis.fetch = () => { throw Error('Unexpected OAuth network egress during authorize test') }
    for (const name of ['constants', 'kv', 'validation', 'flind-oauth-admission']) {
        let contents = tracked('services/oauth-proxy/src/lib/' + name + '.ts')
        if (name === 'kv') contents = contents.replaceAll("'./constants'", "'./constants.ts'")
        writeFileSync(join(temp, name + '.ts'), contents)
    }
    const html = tracked('services/oauth-proxy/src/static/region-picker.html')
    let authorize = tracked('services/oauth-proxy/src/handlers/authorize.ts')
    for (const name of ['constants', 'kv', 'validation', 'flind-oauth-admission']) {
        authorize = authorize.replaceAll('@/lib/' + name, './' + name + '.ts')
    }
    authorize = authorize.replace(
        "import REGION_PICKER_HTML from '../static/region-picker.html'",
        'const REGION_PICKER_HTML = ' + JSON.stringify(html)
    )
    writeFileSync(join(temp, 'authorize.ts'), authorize)
    const { handleAuthorize } = await import(pathToFileURL(join(temp, 'authorize.ts')))
    const { flindOAuthRuntimeReady } = await import(pathToFileURL(join(temp, 'flind-oauth-admission.ts')))
    const { REGION_BASE_URLS } = await import(pathToFileURL(join(temp, 'constants.ts')))
    const env = { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
                  FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' }
    const base = 'https://oauth.flind.example/oauth/authorize/'
    const writes = []
    const reads = []
    let mapping = null
    const kv = {
        get: async (key) => { reads.push(key); return key.startsWith('client:') ? mapping : null },
        put: async (key, value) => { writes.push([key, value]) },
    }
    for (const bad of [
        {},
        { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com', FLIND_OAUTH_EU_ORIGIN: 'https://eu.posthog.com' },
        { FLIND_OAUTH_US_ORIGIN: env.FLIND_OAUTH_US_ORIGIN, FLIND_OAUTH_EU_ORIGIN: env.FLIND_OAUTH_US_ORIGIN },
    ]) {
        const res = await handleAuthorize(new Request(base + '?client_id=test&_region=us'), kv, bad)
        assert.equal(res.status, 503)
        assert.equal(reads.length, 0)
        assert.equal(writes.length, 0)
    }
    console.log('PASS: no owned pair refuses authorization before KV or redirect')

    let res = await handleAuthorize(new Request(base + '?client_id=test'), kv, env)
    assert.equal(res.status, 200)
    const page = await res.text()
    assert.ok(page.includes('Authenticate with Flind'))
    assert.ok(page.includes('US region') && page.includes('EU region'))
    assert.ok(!page.includes('https://us.posthog.com'))
    assert.ok(!page.includes('https://posthog.com'))
    assert.ok(!page.includes('Authenticate with PostHog'))
    console.log('PASS: region picker renders only first-party Flind visible identity and no donor links')

    const us = new URL(base + '?client_id=test&_region=us&state=state-a&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback')
    res = await handleAuthorize(new Request(us), kv, env)
    assert.equal(res.status, 302)
    assert.equal(new URL(res.headers.get('location')).origin, env.FLIND_OAUTH_US_ORIGIN)
    assert.equal(new URL(res.headers.get('location')).searchParams.get('_region'), null)
    assert.ok(writes.some(([key, value]) => key.startsWith('region:') && value === 'us'))
    console.log('PASS: US authorize uses explicitly owned Flind region and never forwards internal region param')

    writes.length = 0; reads.length = 0
    mapping = { us_client_id: 'owned-us', eu_client_id: 'owned-eu',
                redirect_uris: ['http://localhost:3000/callback'], created_at: Date.now() }
    const eu = new URL(base + '?client_id=proxy-client&_region=eu&state=user-state&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback')
    res = await handleAuthorize(new Request(eu), kv, env)
    assert.equal(res.status, 302)
    const target = new URL(res.headers.get('location'))
    assert.equal(target.origin, env.FLIND_OAUTH_EU_ORIGIN)
    assert.equal(target.searchParams.get('client_id'), mapping.eu_client_id)
    assert.equal(target.searchParams.get('redirect_uri'), 'https://oauth.flind.example/oauth/callback/')
    assert.ok(target.searchParams.get('state') !== 'user-state')
    assert.ok(writes.some(([key]) => key.startsWith('pending_callback:')))
    console.log('PASS: EU mapping translates client ID, callback URI and stores a pending nonce')

    writes.length = 0
    res = await handleAuthorize(new Request(base +
        '?client_id=proxy-client&_region=eu&redirect_uri=https%3A%2F%2Fevil.example%2Fsteal'), kv, env)
    assert.equal(res.status, 400)
    assert.equal(writes.length, 0)
    console.log('PASS: unregistered callback URI rejected before any KV writes or redirect')

    mapping = null
    res = await handleAuthorize(new Request(base + '?client_id=test'), kv, env)
    assert.equal(res.status, 200)
    res = await handleAuthorize(new Request(base + '?client_id=test'), kv, env)
    assert.equal(res.status, 200)
    assert.equal(flindOAuthRuntimeReady(env, REGION_BASE_URLS), false)
    console.log('PASS: first-party handler migration does not bypass global unqualified OAuth gate')

    const tests = tracked('services/oauth-proxy/tests/authorize.test.ts')
    assert.ok(tests.includes('blocks %s configuration before redirect or KV I/O'))
    assert.ok(tests.includes('handleAuthorize(request, mockKV, ownedEnv)'))
    console.log('PASS: existing Vitest tests adapted to Flind origins and configured handler signature')
    console.log('Wave154 PASS: source-executed authorization handler, not complete OAuth OIDC/PKCE')
} finally {
    globalThis.fetch = originalFetch
    rmSync(temp, { recursive: true, force: true })
}
