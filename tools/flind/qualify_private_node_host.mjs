import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = new URL('../../packages/node-sdk/', import.meta.url)

test('private Flind Node SDK source and both compiled entrypoints have no vendor default host', () => {
    for (const file of ['src/client.ts', 'dist/client.js', 'dist/client.mjs']) {
        const src = readFileSync(new URL(file, source), 'utf8')
        assert.doesNotMatch(src, /DEFAULT_NODE_HOST/)
        assert.doesNotMatch(src, /https:\/\/us\.i\.posthog\.com/)
        assert.match(src, /requires an explicit owned host/)
        assert.match(src, /hostname\.endsWith\('\.posthog\.com'\)/)
        assert.match(src, /hostname\.endsWith\('\.posthog\.dev'\)/)
        assert.match(src, /hostname === '127\.0\.0\.1'/)
        assert.match(src, /url\.username/)
        assert.match(src, /url\.pathname !== '\/'/)
        assert.match(src, /return url\.origin/)
        assert.match(src, /appHost: options\.appHost === (?:undefined|void 0) \? (?:undefined|void 0) : normalizeHost\(options\.appHost\)/)
    }
})
test('wire tests require CJS and ESM constructor negative controls and local-only capture', () => {
    const src = readFileSync(new URL('../../tools/flind/flind-node-sdk-wire.test.mjs', import.meta.url), 'utf8')
    assert.match(src, /CjsSDK = require\('@flind\/node'\)\.PostHog/)
    assert.match(src, /EsmSDK = \(await import\('@flind\/node'\)\)\.PostHog/)
    assert.match(src, /private Flind Node SDK sends synthetic events to an explicitly local host/)
    assert.match(src, /Flind Node SDK keeps pinned v5\.63\.2 capture wire parity/)
})
