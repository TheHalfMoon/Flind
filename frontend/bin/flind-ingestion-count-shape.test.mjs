import assert from 'node:assert/strict'
import test from 'node:test'

import { parseHogQLCount } from '../../playwright/utils/parse-hogql-count.ts'

test('HogQL zero is accepted only when count() actually returned zero', () => {
    assert.equal(parseHogQLCount({ results: [[0]] }), 0)
    assert.equal(parseHogQLCount({ results: [['0']] }), 0)
    assert.equal(parseHogQLCount({ results: [[3]] }), 3)
    assert.equal(parseHogQLCount({ results: [['16']] }), 16)
})

test('missing or malformed query results cannot pass tenant-isolation negative control', () => {
    for (const payload of [
        null, undefined, {}, { results: null }, { results: [] }, { results: [[]] },
        { results: [[null]] }, { results: [[undefined]] }, { results: [[false]] },
        { results: [['']] }, { results: [['NaN']] }, { results: [['0.0']] },
        { results: [[-1]] }, { results: [[1.5]] }, { results: [[Infinity]] },
        { results: [[Number.MAX_SAFE_INTEGER + 1]] },
        { results: [[0], [0]] }, { results: [[0, 1]] },
    ]) {
        assert.throws(() => parseHogQLCount(payload), undefined, JSON.stringify(payload))
    }
})
