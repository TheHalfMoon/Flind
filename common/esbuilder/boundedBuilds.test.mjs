import assert from 'node:assert/strict'
import test from 'node:test'

import { productionBuildConcurrency, runBoundedBuilds } from './boundedBuilds.mjs'

test('default production scheduler preserves previous full parallelism', () => {
    const previous = process.env.FLIND_BUILD_MAX_PARALLEL
    delete process.env.FLIND_BUILD_MAX_PARALLEL
    try {
        assert.equal(productionBuildConcurrency(11), 11)
        assert.equal(productionBuildConcurrency(11, ''), 11)
        assert.equal(productionBuildConcurrency(0), 0)
    } finally {
        if (previous === undefined) delete process.env.FLIND_BUILD_MAX_PARALLEL
        else process.env.FLIND_BUILD_MAX_PARALLEL = previous
    }
})

test('explicit environment override is honored in production', () => {
    const previous = process.env.FLIND_BUILD_MAX_PARALLEL
    process.env.FLIND_BUILD_MAX_PARALLEL = '1'
    try {
        assert.equal(productionBuildConcurrency(11), 1)
    } finally {
        if (previous === undefined) delete process.env.FLIND_BUILD_MAX_PARALLEL
        else process.env.FLIND_BUILD_MAX_PARALLEL = previous
    }
})

test('explicit local limit is capped to the number of builds', () => {
    assert.equal(productionBuildConcurrency(11, '1'), 1)
    assert.equal(productionBuildConcurrency(11, '3'), 3)
    assert.equal(productionBuildConcurrency(11, '999'), 11)
    assert.equal(productionBuildConcurrency(0, '3'), 0)
})

test('malformed or unsafe concurrency never falls back to unbounded mode', () => {
    for (const invalid of ['0', '-1', '01', ' 1', '1.5', '1e3', 'Infinity', '1000', 'foo', 2, null]) {
        assert.throws(() => productionBuildConcurrency(11, invalid), RangeError)
    }
    assert.throws(() => productionBuildConcurrency(-1, '1'), RangeError)
    assert.throws(() => productionBuildConcurrency(1.5, '1'), RangeError)
})

test('bounded scheduler serializes expensive tasks when limit=1', async () => {
    let active = 0
    let peak = 0
    const visited = []
    await runBoundedBuilds(
        Array.from({ length: 8 }, (_, i) => i),
        async (value) => {
            active += 1
            peak = Math.max(peak, active)
            await new Promise((resolve) => setImmediate(resolve))
            visited.push(value)
            active -= 1
        },
        1
    )
    assert.equal(peak, 1)
    assert.deepEqual(visited, [0, 1, 2, 3, 4, 5, 6, 7])
})

test('bounded scheduler respects multi-worker cap and processes each build once', async () => {
    let active = 0
    let peak = 0
    const seen = []
    await runBoundedBuilds(
        Array.from({ length: 11 }, (_, i) => i),
        async (value) => {
            active += 1
            peak = Math.max(peak, active)
            await new Promise((resolve) => setImmediate(resolve))
            seen.push(value)
            active -= 1
        },
        3
    )
    assert.equal(peak, 3)
    assert.deepEqual(
        [...seen].sort((a, b) => a - b),
        Array.from({ length: 11 }, (_, i) => i)
    )
})

test('worker failure fails the build rather than claiming partial success', async () => {
    const visited = []
    await assert.rejects(
        runBoundedBuilds(
            [1, 2, 3],
            async (value) => {
                visited.push(value)
                if (value === 2) throw new Error('synthetic build failure')
            },
            1
        ),
        /synthetic build failure/
    )
    assert.deepEqual(visited, [1, 2])
})

test('empty build graph is a valid no-op, invalid inputs are refused', async () => {
    let invoked = false
    await runBoundedBuilds(
        [],
        async () => {
            invoked = true
        },
        0
    )
    assert.equal(invoked, false)
    await assert.rejects(
        runBoundedBuilds([1], async () => undefined, 0),
        RangeError
    )
    await assert.rejects(
        runBoundedBuilds({}, async () => undefined, 1),
        TypeError
    )
})
