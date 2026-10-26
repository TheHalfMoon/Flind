#!/usr/bin/env node
// Regression: private Flind package display metadata, not protocol/source migration.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const root = process.env.FLIND_SOURCE_ROOT || resolve(fileURLToPath(new URL('../..', import.meta.url)))
const candidate = process.env.FLIND_TEST_REF || 'HEAD'
const baseline = '7f263af2983b947dc421a9283d89351f8f5746db'
const packages = [
  'products/desktop/apps/code/package.json',
  'products/desktop/packages/api-client/package.json',
  'packages/agent/packages/agent/package.json',
]
const allowedKeys = new Set(['description', 'author', 'homepage', 'repository'])
function fromGit(ref, path) {
  return execFileSync('git', ['-C', root, 'show', ref + ':' + path], {
    encoding: 'utf8', timeout: 30000, maxBuffer: 2 * 1024 * 1024,
  })
}
for (const path of packages) {
  const before = JSON.parse(fromGit(baseline, path))
  const after = JSON.parse(fromGit(candidate, path))
  assert.equal(after.private, true, path)
  assert.ok(after.name.startsWith('@flind/'), path)
  const changed = new Set(Object.keys(after).filter(k => JSON.stringify(after[k]) !== JSON.stringify(before[k])))
  assert.ok(changed.size > 0, path)
  for (const key of changed) assert.ok(allowedKeys.has(key), path + ': ' + key)
  for (const key of ['name', 'version', 'private', 'license', 'scripts',
    'dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies',
    'exports', 'main', 'types']) {
    assert.deepEqual(after[key], before[key], path + ': ' + key)
  }
  for (const key of allowedKeys) {
    if (after[key] !== undefined) assert.ok(!JSON.stringify(after[key]).toLowerCase().includes('posthog'), path + ': ' + key)
  }
  if (path.includes('apps/code/')) assert.equal(after.homepage, 'https://github.com/TheHalfMoon/Flind')
  if (path.includes('packages/agent/packages/agent')) {
    assert.equal(after.repository?.url, 'git+https://github.com/TheHalfMoon/Flind.git')
  }
  console.log('PASS first-party metadata-only: ' + path)
}
for (const notice of ['LICENSE', 'products/desktop/LICENSE']) {
  assert.equal(fromGit(baseline, notice), fromGit(candidate, notice))
}
console.log('PASS: legal license notices retained and 3 manifests unchanged beyond display metadata')
