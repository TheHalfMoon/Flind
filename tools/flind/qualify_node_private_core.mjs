import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const root = resolve(fileURLToPath(new URL('../../', import.meta.url)))
const read = (path) => readFileSync(resolve(root, path), 'utf8')
function walk(directory) {
    return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
        const path = join(directory, entry.name)
        return entry.isDirectory() ? walk(path) : [path]
    })
}

test('Node SDK consumes private core via an explicit pinned local workspace dependency', () => {
    const sdk = JSON.parse(read('packages/node-sdk/package.json'))
    const core = JSON.parse(read('packages/core/package.json'))
    const workspace = read('pnpm-workspace.yaml')
    const lockfile = read('pnpm-lock.yaml')
    assert.equal(sdk.dependencies['@flind/core'], 'workspace:*')
    assert.equal(sdk.dependencies['@posthog/core'], undefined)
    assert.equal(core.name, '@flind/core')
    assert.equal(core.version, '1.64.1')
    assert.equal(core.private, true)
    assert.match(workspace, /- packages\/core/)
    assert.match(lockfile, /  packages\/core:\s+dependencies:\s+'@flind\/types':\s+specifier: workspace:\*\s+version: link:\.\.\/types/)
    assert.match(lockfile, /  packages\/node-sdk:[\s\S]*?'@flind\/core':\s+specifier: workspace:\*\s+version: link:\.\.\/core/)
    assert.doesNotMatch(read('packages/node-sdk/README.md'), /runtime dependency and inherited/)
})

test('all staged Node SDK source and runtime imports resolve to the private Flind core', () => {
    let changed = 0
    for (const folder of ['src', 'dist']) {
        const files = walk(resolve(root, 'packages/node-sdk', folder))
        for (const path of files) {
            if (!/\.(?:js|mjs|ts|json|map)$/.test(path)) continue
            const code = readFileSync(path, 'utf8')
            assert.doesNotMatch(code, /@posthog\/core/, path)
            if (code.includes('@flind/core')) changed += 1
        }
    }
    assert.ok(changed >= 70, 'Expected the complete source and compiled API surface to migrate')
    assert.match(read('packages/node-sdk/dist/entrypoints/index.node.js'), /@flind\/core/)
    assert.match(read('packages/node-sdk/dist/entrypoints/index.edge.js'), /@flind\/core/)
})

test('original core license notices stay preserved and Node wire CI copies both packages', () => {
    const original = JSON.parse(read('packages/core/UPSTREAM_PACKAGE.json'))
    const core = JSON.parse(read('packages/core/package.json'))
    assert.equal(original.name, '@posthog/core')
    assert.equal(core.name, '@flind/core')
    assert.match(read('packages/core/NOTICE.md'), /Apache-2\.0 and MIT/)
    for (const file of [
        '.github/workflows/flind-node-sdk-owned-host.yml',
        '.github/workflows/flind-node-sdk-qualification.yml',
        '.github/workflows/flind-node-sdk-wire.yml',
    ]) {
        assert.match(read(file), /cp -R packages\/core/)
    }
})
