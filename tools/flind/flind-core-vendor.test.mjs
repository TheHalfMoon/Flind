import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join, resolve, relative } from 'node:path'
import test from 'node:test'

const require = createRequire(import.meta.url)
const donorRoot = resolve(dirname(require.resolve('@posthog/core')), '..')
const flindRoot = resolve(dirname(require.resolve('@flind/core')), '..')

function allFiles(directory, base = directory) {
    return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
        const file = join(directory, entry.name)
        return entry.isDirectory() ? allFiles(file, base) : [relative(base, file)]
    }).sort()
}

test('published core package metadata, legal notices and Flind namespace are preserved', () => {
    const original = JSON.parse(readFileSync(join(donorRoot, 'package.json'), 'utf8'))
    const snapshot = JSON.parse(readFileSync(join(flindRoot, 'UPSTREAM_PACKAGE.json'), 'utf8'))
    const fork = JSON.parse(readFileSync(join(flindRoot, 'package.json'), 'utf8'))
    assert.deepEqual(snapshot, original)
    assert.equal(fork.name, '@flind/core')
    assert.equal(fork.version, '1.64.1')
    assert.equal(fork.private, true)
    assert.deepEqual(fork.exports, original.exports)
    assert.deepEqual(fork.typesVersions, original.typesVersions)
    const expectedDependencies = { ...original.dependencies }
    delete expectedDependencies['@posthog/types']
    expectedDependencies['@flind/types'] = 'workspace:*'
    assert.deepEqual(fork.dependencies, expectedDependencies)
    assert.deepEqual(readFileSync(join(flindRoot, 'LICENSE')), readFileSync(join(donorRoot, 'LICENSE')))
    assert.match(readFileSync(join(flindRoot, 'NOTICE.md'), 'utf8'), /Apache-2.0 and MIT/)
})

test('core source and runtime match the pinned archive with only the approved type-namespace substitution', () => {
    for (const folder of ['src', 'dist', 'surveys']) {
        const left = join(donorRoot, folder)
        const right = join(flindRoot, folder)
        const files = allFiles(left)
        assert.deepEqual(allFiles(right), files, 'staged ' + folder + ' file inventory differs')
        for (const file of files) {
            const originalBytes = readFileSync(join(left, file))
            const expectedBytes = file.endsWith('.ts')
                ? Buffer.from(originalBytes.toString('utf8').replaceAll('@posthog/types', '@flind/types'), 'utf8')
                : originalBytes
            assert.deepEqual(readFileSync(join(right, file)), expectedBytes, folder + '/' + file)
        }
    }
})

test('full CommonJS core entrypoint and subpaths retain pinned published exports', () => {
    for (const path of ['', '/error-tracking', '/surveys', '/testing', '/utils']) {
        const original = require('@posthog/core' + path)
        const flind = require('@flind/core' + path)
        assert.deepEqual(Object.keys(flind).sort(), Object.keys(original).sort(), path || '.')
    }
    assert.equal(typeof require('@flind/core').PostHogCoreStateless, 'function')
})

test('full ESM core entrypoint and subpaths retain pinned published exports', async () => {
    for (const path of ['', '/error-tracking', '/surveys', '/testing', '/utils']) {
        const original = await import('@posthog/core' + path)
        const flind = await import('@flind/core' + path)
        assert.deepEqual(Object.keys(flind).sort(), Object.keys(original).sort(), path || '.')
    }
    assert.equal(typeof (await import('@flind/core')).PostHogCoreStateless, 'function')
})
