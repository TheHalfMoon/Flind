#!/usr/bin/env node
/* Wave152: execute original Flind discovery TypeScript without full monorepo JS deps. */
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
const working = mkdtempSync(join(tmpdir(), 'flind-owned-oauth-metadata-'))
const previousFetch = globalThis.fetch
try {
    for (const part of ['constants', 'flind-oauth-admission']) {
        writeFileSync(join(working, part + '.ts'), tracked('services/oauth-proxy/src/lib/' + part + '.ts'))
    }
    const metadata = tracked('services/oauth-proxy/src/handlers/metadata.ts')
        .replaceAll('@/lib/constants', './constants.ts')
        .replaceAll('@/lib/flind-oauth-admission', './flind-oauth-admission.ts')
    writeFileSync(join(working, 'metadata.ts'), metadata)
    const { handleMetadata, handleOpenIdConfiguration, handleClientManifest } =
        await import(pathToFileURL(join(working, 'metadata.ts')))
    const proxy = 'https://oauth.flind.example'
    const us = 'https://us.flind.example'
    const owned = { FLIND_OAUTH_US_ORIGIN: us }
    const kv = {}
    const calls = []
    globalThis.fetch = async (url) => {
        calls.push(url)
        if (url.endsWith('/auth.md')) {
            return new Response('Authorize at ' + us + '/oauth/authorize/ and keep ' +
                'https://us.flind.example.evil/not-owned', { status: 200 })
        }
        return new Response(JSON.stringify({
            issuer: us,
            authorization_endpoint: us + '/oauth/authorize/',
            nested: { skill: us + '/auth.md' },
            posthog_base_url: us,  // persisted provider field awaiting schema migration
            deceptive: us + '.evil/oauth/token/',
        }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }

    let response = await handleMetadata(new Request(proxy + '/.well-known/oauth-authorization-server'), kv, {})
    assert.equal(response.status, 503)
    assert.equal(calls.length, 0)
    console.log('PASS: no Flind backend configuration refuses discovery before any outbound HTTP')

    response = await handleMetadata(new Request(proxy + '/.well-known/oauth-authorization-server'), kv,
        { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com' })
    assert.equal(response.status, 503)
    assert.equal(calls.length, 0)
    console.log('PASS: original external OAuth host cannot be supplied directly')

    const request = new Request(proxy + '/.well-known/oauth-authorization-server')
    response = await handleMetadata(request, kv, owned)
    assert.equal(response.status, 200)
    const body = await response.json()
    assert.equal(body.issuer, proxy)
    assert.equal(body.authorization_endpoint, proxy + '/oauth/authorize/')
    assert.equal(body.nested.skill, proxy + '/auth.md')
    assert.equal(body.posthog_base_url, us)
    assert.equal(body.deceptive, us + '.evil/oauth/token/')
    assert.deepEqual(calls, [us + '/.well-known/oauth-authorization-server'])
    console.log('PASS: real discovery handler fetches owned Flind region and rewrites only origin-bound URLs')

    await handleMetadata(request, kv, owned)
    assert.equal(calls.length, 1)
    console.log('PASS: cache prevents redundant owned HTTP calls')

    response = await handleMetadata(request, kv, { FLIND_OAUTH_US_ORIGIN: 'https://different.flind.example' })
    assert.equal(response.status, 200)
    assert.equal(calls.length, 2)
    assert.equal(calls[1], 'https://different.flind.example/.well-known/oauth-authorization-server')
    console.log('PASS: cache partitioned by configured backend owner')

    response = await handleOpenIdConfiguration(
        new Request(proxy + '/.well-known/openid-configuration'), kv, owned)
    assert.equal(response.status, 200)
    assert.equal(calls.at(-1), us + '/.well-known/openid-configuration')
    console.log('PASS: OpenID discovery path uses explicitly owned backend')

    response = await handleClientManifest(new Request(proxy + '/auth.md'), kv, owned)
    assert.equal(response.status, 200)
    const manifest = await response.text()
    assert.ok(manifest.includes(proxy + '/oauth/authorize/'))
    assert.ok(manifest.includes(us + '.evil/not-owned'))
    assert.equal(calls.at(-1), us + '/auth.md')
    console.log('PASS: agent auth manifest fetched from Flind and lookalike URL not rewritten')

    assert.ok(!metadata.includes('POSTHOG_US_BASE_URL'))
    const originalVitest = tracked('services/oauth-proxy/tests/metadata.test.ts')
    assert.ok(originalVitest.includes('fails closed when no owned Flind origin is configured'))
    assert.ok(originalVitest.includes('handleMetadata(request, emptyKv, ownedEnv)'))
    console.log('PASS: original metadata regressions migrated to first-party handler signature')
    console.log('Wave152 PASS: source-executed discovery only, not complete OAuth OIDC/PKCE')
} finally {
    globalThis.fetch = previousFetch
    rmSync(working, { recursive: true, force: true })
}
