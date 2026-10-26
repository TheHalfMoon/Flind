#!/usr/bin/env node
/**
 * Wave151: actual Flind regional-admission TypeScript execution under Node 24.
 * No external modules, OAuth keys, providers, network requests or deployments.
 */
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const repo = process.env.FLIND_SOURCE_ROOT || process.cwd()
const ref = process.env.FLIND_TEST_REF || 'HEAD'
function source(path) {
    return execFileSync('git', ['-C', repo, 'show', ref + ':' + path], {
        encoding: 'utf8', timeout: 35000, maxBuffer: 2_000_000,
    })
}

const temp = mkdtempSync(join(tmpdir(), 'flind-oauth-region-'))
try {
    const originSource = source('services/oauth-proxy/src/lib/flind-oauth-admission.ts')
    const path = join(temp, 'flind-oauth-admission.ts')
    writeFileSync(path, originSource)
    const { flindOAuthRuntimeReady } = await import(pathToFileURL(path))
    const existing = source('services/oauth-proxy/src/lib/constants.ts')
    const index = source('services/oauth-proxy/src/index.ts')
    const tests = source('services/oauth-proxy/tests/router.test.ts')
    const actual = {
        us: existing.match(/POSTHOG_US_BASE_URL\s*=\s*'([^']+)'/)?.[1],
        eu: existing.match(/POSTHOG_EU_BASE_URL\s*=\s*'([^']+)'/)?.[1],
    }
    assert.ok(actual.us && actual.eu)
    assert.match(actual.us, /posthog\.com/)
    assert.match(actual.eu, /posthog\.com/)
    const owned = { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example',
                    FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' }
    assert.equal(flindOAuthRuntimeReady({}, actual), false)
    console.log('PASS: absent Flind regional owners fail closed')
    assert.equal(flindOAuthRuntimeReady(owned, actual), false)
    console.log('PASS: even explicitly configured Flind env cannot enable inherited vendor handler routes')
    assert.equal(flindOAuthRuntimeReady({
        FLIND_OAUTH_US_ORIGIN: actual.us, FLIND_OAUTH_EU_ORIGIN: actual.eu,
    }, actual), false)
    console.log('PASS: matching old upstream vendor destinations cannot bypass the gate')
    assert.equal(flindOAuthRuntimeReady(owned, {
        us: owned.FLIND_OAUTH_US_ORIGIN, eu: owned.FLIND_OAUTH_EU_ORIGIN,
    }), true)
    console.log('PASS: migrated same-owned origins could qualify the region gate')
    for (const config of [
        { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' },
        { FLIND_OAUTH_US_ORIGIN: 'https://us.posthog.com.evil', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' },
        { FLIND_OAUTH_US_ORIGIN: 'http://unowned.example', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' },
        { FLIND_OAUTH_US_ORIGIN: 'https://token@us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' },
        { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example/oauth', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' },
        { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example/?token=a', FLIND_OAUTH_EU_ORIGIN: 'https://eu.flind.example' },
        { FLIND_OAUTH_US_ORIGIN: 'https://us.flind.example', FLIND_OAUTH_EU_ORIGIN: 'https://us.flind.example' },
    ]) {
        assert.equal(flindOAuthRuntimeReady(config, {
            us: config.FLIND_OAUTH_US_ORIGIN, eu: config.FLIND_OAUTH_EU_ORIGIN,
        }), false, JSON.stringify(config))
    }
    console.log('PASS: vendor, userinfo, HTTP remote, path, query and shared-region configurations refused')
    assert.equal(flindOAuthRuntimeReady({
        FLIND_OAUTH_US_ORIGIN: 'http://127.0.0.1:18001',
        FLIND_OAUTH_EU_ORIGIN: 'http://localhost:18002',
    }, { us: 'http://127.0.0.1:18001', eu: 'http://localhost:18002' }), true)
    console.log('PASS: two distinct local Flind test origins are permitted')
    const gate = index.indexOf('!flindOAuthRuntimeReady(env, REGION_BASE_URLS)')
    const dispatch = index.indexOf('return await route.handler(request, env.AUTH_KV, env)')
    assert.ok(gate > 0 && dispatch > gate)
    assert.match(index.slice(gate, dispatch), /status:\s*503/)
    assert.match(index.slice(gate, dispatch), /no-store/)
    assert.ok(index.includes('requiresRegionalBackend: false'))
    console.log('PASS: admission runs BEFORE auth handlers and denies with uncacheable HTTP 503')
    assert.ok(tests.includes('not.toHaveBeenCalled()'))
    assert.ok(tests.includes('configured owned env cannot bypass inherited handler targets'))
    console.log('PASS: original router regression asserts zero upstream fetches and KV writes')
    console.log('Wave151 PASS: source-backed owner-only regional gate, not a full OAuth integration proof')
} finally {
    rmSync(temp, { recursive: true, force: true })
}
