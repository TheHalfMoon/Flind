#!/usr/bin/env node
/* Wave153: run production Flind OAuth dual-registration TS using fake fetch/KV. */
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const root = process.env.FLIND_SOURCE_ROOT || process.cwd()
const ref = process.env.FLIND_TEST_REF || 'HEAD'
function tracked(path) {
    return execFileSync('git', ['-C', root, 'show', ref + ':' + path], {
        encoding: 'utf8', timeout: 45000, maxBuffer: 2_000_000,
    })
}
const temp = mkdtempSync(join(tmpdir(), 'flind-oauth-dual-register-'))
const savedFetch = globalThis.fetch
try {
    const files = [
        ['constants.ts', tracked('services/oauth-proxy/src/lib/constants.ts')],
        ['flind-oauth-admission.ts', tracked('services/oauth-proxy/src/lib/flind-oauth-admission.ts')],
        ['kv.ts', tracked('services/oauth-proxy/src/lib/kv.ts').replaceAll("'./constants'", "'./constants.ts'")],
        ['register.ts', tracked('services/oauth-proxy/src/handlers/register.ts')
            .replaceAll('@/lib/flind-oauth-admission', './flind-oauth-admission.ts')
            .replaceAll('@/lib/kv', './kv.ts')],
    ]
    for (const [name, content] of files) writeFileSync(join(temp, name), content)
    const { handleRegister } = await import(pathToFileURL(join(temp, 'register.ts')))
    const { flindOAuthRuntimeReady } = await import(pathToFileURL(join(temp, 'flind-oauth-admission.ts')))
    const { REGION_BASE_URLS } = await import(pathToFileURL(join(temp, 'constants.ts')))
    const owned = { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
                    FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' }
    const url = 'https://oauth.flind.example/oauth/register/'
    let writes = []
    let calls = []
    let failure = ''
    const kv = { put: async (key, body) => writes.push([key, body]) }
    globalThis.fetch = async (target, init) => {
        calls.push({ target, init })
        const region = target.startsWith(owned.FLIND_OAUTH_US_ORIGIN) ? 'us' : 'eu'
        const status = failure === 'both' || failure === region ? 400 : 201
        return new Response(
            JSON.stringify(status === 201 ? { client_id: region + '-owned-client', client_name: 'Flind' }
                                        : { error: 'invalid_client_metadata' }),
            { status, headers: { 'Content-Type': 'application/json' } }
        )
    }
    function request() {
        return new Request(url, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_name: 'Flind', redirect_uris: ['http://localhost:3000/callback'] }),
        })
    }
    for (const env of [
        {},
        { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com', FLIND_OAUTH_EU_ORIGIN: 'https://eu.posthog.com' },
        { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://us.flind.example' },
        { FLIND_OAUTH_US_ORIGIN: 'http://us.flind.example', FLIND_OAUTH_EU_ORIGIN: owned.FLIND_OAUTH_EU_ORIGIN },
    ]) {
        const res = await handleRegister(request(), kv, env)
        assert.equal(res.status, 503)
        assert.equal(calls.length, 0)
        assert.equal(writes.length, 0)
    }
    console.log('PASS: unconfigured, old vendor, same-region and invalid origins refuse before fetch/KV')

    let response = await handleRegister(request(), kv, owned)
    assert.equal(response.status, 201)
    assert.deepEqual(calls.map(call => call.target), [
        'https://us.flind.example/oauth/register/',
        'https://eu.flind.example/oauth/register/',
    ])
    assert.equal(calls.length, 2)
    for (const { init } of calls) {
        assert.equal(init.method, 'POST')
        const body = JSON.parse(init.body)
        assert.ok(body.redirect_uris.includes('http://localhost:3000/callback'))
        assert.ok(body.redirect_uris.includes('https://oauth.flind.example/oauth/callback/'))
    }
    assert.equal(writes.length, 1)
    const mapping = JSON.parse(writes[0][1])
    assert.equal(mapping.us_client_id, 'us-owned-client')
    assert.equal(mapping.eu_client_id, 'eu-owned-client')
    assert.deepEqual(mapping.redirect_uris, ['http://localhost:3000/callback'])
    console.log('PASS: real register handler calls only owned regions and saves correct original client mapping')

    calls = []; writes = []; failure = 'eu'
    response = await handleRegister(request(), kv, owned)
    assert.equal(response.status, 400)
    assert.equal(writes.length, 0)
    assert.equal(calls.length, 2)
    console.log('PASS: partial EU registration failure does not commit an invalid mapping')

    calls = []; writes = []; failure = 'both'
    response = await handleRegister(request(), kv, owned)
    assert.equal(response.status, 400)
    assert.equal(writes.length, 0)
    console.log('PASS: two failed upstream registrations cannot register a client')

    assert.equal(flindOAuthRuntimeReady(owned, REGION_BASE_URLS), false)
    console.log('PASS: public Worker still blocked until authorize/token/JWKS/issuers are also migrated')
    const original = tracked('services/oauth-proxy/tests/register.test.ts')
    assert.ok(original.includes('refuses %s before any fetch or KV write'))
    assert.ok(original.includes('handleRegister(request, mockKV, ownedEnv)'))
    console.log('PASS: original Vitest registration regressions target Flind-owned first-party backend')
    console.log('Wave153 PASS: source-executed registration, not complete OAuth certification')
} finally {
    globalThis.fetch = savedFetch
    rmSync(temp, { recursive: true, force: true })
}
