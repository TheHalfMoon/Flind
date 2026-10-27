#!/usr/bin/env node
// Wave195: execute the grouping-key function from Flind's tracked production
// joined-ingestion-pipeline.ts, rather than a rewritten helper or mock.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'
import test from 'node:test'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const source = readFileSync(
    path.join(root, 'nodejs/src/ingestion/pipelines/analytics/joined-ingestion-pipeline.ts'),
    'utf8'
)
const matches = source.match(/^function getTokenAndDistinctId\(input: EventSubpipelineInput\): string \{[\s\S]*?^\}/gm)
assert.equal(matches?.length, 1, 'original Flind joined-pipeline grouping function must exist once')
const grouped = vm.runInNewContext(
    stripTypeScriptTypes(matches[0], { mode: 'strip' }) + '\ngetTokenAndDistinctId',
    Object.create(null),
    { filename: 'flind-original-joined-ingestion-group-key.js', timeout: 1000 }
)
const key = (token, distinctId) => grouped({
    headers: { token },
    event: { distinct_id: distinctId },
})

test('original production joined pipeline passes this key function to concurrentlyPerGroup', () => {
    assert.equal(source.split('.concurrentlyPerGroup(getTokenAndDistinctId,').length, 2)
})

test('distinct project token and distinct_id pairs cannot collide via colon splitting', () => {
    // The old implementation returned "alpha:beta:gamma" for BOTH pairs.
    assert.equal('alpha:beta' + ':' + 'gamma', 'alpha' + ':' + 'beta:gamma')
    assert.notEqual(key('alpha:beta', 'gamma'), key('alpha', 'beta:gamma'))
})

test('different empty/colon identity pairs remain distinct', () => {
    assert.notEqual(key('', ':'), key(':', ''))
    assert.notEqual(key('', 'a:b'), key('a', ':b'))
})

test('identical identities keep deterministic grouping across batches', () => {
    assert.equal(key('tenant-one', 'customer:7'), key('tenant-one', 'customer:7'))
    assert.notEqual(key('tenant-one', 'customer:7'), key('tenant-two', 'customer:7'))
    assert.notEqual(key('tenant-one', 'customer:7'), key('tenant-one', 'customer:8'))
})

test('missing optional identity fields preserve empty-string semantics', () => {
    assert.equal(grouped({ headers: {}, event: {} }), key('', ''))
    assert.equal(grouped({ headers: { token: null }, event: { distinct_id: null } }), key('', ''))
})

test('unicode, colon and escaped characters are not confused', () => {
    assert.notEqual(key('😀:', 'x'), key('😀', ':x'))
    assert.notEqual(key('a\n:', '\\x'), key('a\n', ':\\x'))
    assert.notEqual(key('α:', 'β'), key('α', ':β'))
})

test('exhaustive 1,600 synthetic identity pairs have unique keys', () => {
    const alphabet = ['a', ':', '😀']
    const values = ['']
    for (let length = 1; length <= 3; length++) {
        let words = ['']
        for (let i = 0; i < length; i++) {
            words = words.flatMap((prefix) => alphabet.map((symbol) => prefix + symbol))
        }
        values.push(...words)
    }
    assert.equal(values.length, 40)
    const seen = new Map()
    for (const token of values) {
        for (const distinctId of values) {
            const id = key(token, distinctId)
            assert.equal(typeof id, 'string')
            assert.equal(seen.has(id), false, 'group key collision for ' + JSON.stringify([token, distinctId]))
            seen.set(id, [token, distinctId])
        }
    }
    assert.equal(seen.size, 1600)
})
