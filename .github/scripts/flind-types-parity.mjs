// Flind private types: byte-verified donor archive and CJS/ESM compatibility.
// Usage: node .github/scripts/flind-types-parity.mjs <unpacked-original-package>
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

assert.ok(process.argv[2], 'Pass the extracted original npm package directory')
const original = resolve(process.argv[2])
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const staged = join(root, 'packages/types')

function files(dir) {
    const output = []
    function walk(current) {
        for (const item of readdirSync(current).sort()) {
            const abs = join(current, item)
            if (statSync(abs).isDirectory()) walk(abs)
            else output.push(relative(dir, abs).split('\\').join('/'))
        }
    }
    walk(dir)
    return output.sort()
}

const originalFiles = files(original)
const stagedFiles = files(staged)
assert.equal(originalFiles.length, 78, 'Pinned source file count drift')
assert.deepEqual(
    stagedFiles.filter((name) => !['NOTICE.md', 'UPSTREAM_PACKAGE.json'].includes(name)),
    originalFiles,
    'Staging must contain exactly all original files and two provenance documents'
)
for (const name of originalFiles) {
    if (name === 'package.json') continue
    assert.deepEqual(readFileSync(join(staged, name)), readFileSync(join(original, name)), `Original byte mismatch: ${name}`)
}
assert.deepEqual(readFileSync(join(staged, 'UPSTREAM_PACKAGE.json')), readFileSync(join(original, 'package.json')))

const donor = JSON.parse(readFileSync(join(original, 'package.json'), 'utf8'))
const flind = JSON.parse(readFileSync(join(staged, 'package.json'), 'utf8'))
assert.equal(donor.name, '@posthog/types')
assert.equal(donor.version, '1.421.0')
assert.equal(flind.name, '@flind/types')
assert.equal(flind.private, true)
assert.equal(flind.version, donor.version)
assert.equal(flind.license, donor.license)
assert.equal(flind.repository.url, 'https://github.com/TheHalfMoon/Flind.git')
for (const key of ['main', 'module', 'types', 'exports', 'devDependencies', 'scripts']) {
    assert.deepEqual(flind[key], donor[key], `Compatibility metadata drift: ${key}`)
}
for (const name of ['LICENSE', 'NOTICE.md', 'README.md', 'UPSTREAM_PACKAGE.json']) {
    assert.ok(flind.files.includes(name), `Provenance excluded from files manifest: ${name}`)
}

const require = createRequire(import.meta.url)
for (const entry of ['dist/index.js', 'dist/index.mjs']) {
    const originalEntry = join(original, entry)
    const stagedEntry = join(staged, entry)
    const upstreamExports = entry.endsWith('.mjs')
        ? await import(pathToFileURL(originalEntry).href)
        : require(originalEntry)
    const flindExports = entry.endsWith('.mjs')
        ? await import(pathToFileURL(stagedEntry).href)
        : require(stagedEntry)
    assert.deepEqual(Object.keys(flindExports).sort(), Object.keys(upstreamExports).sort(), `Runtime ABI exports changed: ${entry}`)
}
console.log(`PASS: ${originalFiles.length} source/license files, original metadata, private namespace and CJS/ESM ABI`)
