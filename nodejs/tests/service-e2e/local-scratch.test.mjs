import assert from 'node:assert/strict'
import { mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'node:test'

import { createOwnedLocalScratch } from './local-scratch.mjs'

function fixture(t) {
    const root = mkdtempSync(path.join(os.tmpdir(), 'flind-scratch-test-'))
    t.after(() => rmSync(root, { recursive: true, force: true }))
    return root
}

test('creates owned temporary scratch as sibling and cleans it', (t) => {
    const checkout = fixture(t)
    const scratch = createOwnedLocalScratch(checkout, { requiredBytes: 0 })
    assert.equal(path.dirname(scratch.path), path.dirname(checkout))
    assert.ok(scratch.path !== checkout)
    assert.ok(scratch.freeBytes() > 0)
    assert.equal(readFileSync(path.join(scratch.path, '.owner'), 'utf8'), 'FLIND_RUST_NODE_E2E_SCRATCH_V1\n')
    scratch.cleanup()
    assert.throws(() => scratch.cleanup())
})

test('tampering with scratch marker refuses deletion', (t) => {
    const checkout = fixture(t)
    const scratch = createOwnedLocalScratch(checkout, { requiredBytes: 0 })
    t.after(() => rmSync(scratch.path, { recursive: true, force: true }))
    writeFileSync(path.join(scratch.path, '.owner'), 'unowned\n')
    assert.throws(() => scratch.cleanup(), /unowned/)
    assert.equal(readFileSync(path.join(scratch.path, '.owner'), 'utf8'), 'unowned\n')
})

test('rejects a symlink to another checkout', (t) => {
    const checkout = fixture(t)
    const alias = checkout + '-symlink'
    symlinkSync(checkout, alias, 'dir')
    t.after(() => rmSync(alias, { force: true }))
    assert.throws(() => createOwnedLocalScratch(alias, { requiredBytes: 0 }), /real directory/)
})

test('rejects insufficient disk before allocating scratch', (t) => {
    const checkout = fixture(t)
    const count = () => readdirSync(path.dirname(checkout)).filter((f) => f.startsWith('.flind-rust-node-e2e-')).length
    const before = count()
    assert.throws(() => createOwnedLocalScratch(checkout, { requiredBytes: Number.MAX_SAFE_INTEGER }), /reserve/)
    assert.equal(count(), before)
})
