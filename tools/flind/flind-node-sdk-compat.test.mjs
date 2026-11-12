import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import test from 'node:test'

const require = createRequire(import.meta.url)

test('CJS Node SDK API remains ABI-compatible with the pinned donor release', () => {
    const donor = require('posthog-node')
    const flind = require('@flind/node')
    assert.deepEqual(Object.keys(flind).sort(), Object.keys(donor).sort())
    assert.equal(typeof flind.PostHog, 'function')
})

test('ESM Node SDK API remains ABI-compatible with the pinned donor release', async () => {
    const donor = await import('posthog-node')
    const flind = await import('@flind/node')
    assert.deepEqual(Object.keys(flind).sort(), Object.keys(donor).sort())
    assert.equal(typeof flind.PostHog, 'function')
})

test('the copied LICENSE remains byte-identical to the published package', () => {
    const license = (name) => readFileSync(resolve(dirname(require.resolve(name)), '../../LICENSE'))
    const original = license('posthog-node')
    const copied = license('@flind/node')
    assert.deepEqual(copied, original)
})
