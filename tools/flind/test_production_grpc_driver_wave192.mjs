#!/usr/bin/env node
/**
 * Wave192: execute Flind's tracked production GrpcStreamIngestDriver with
 * mocked collaborators (NOT a production Kafka/ClickHouse E2E).
 *
 * Zero package installation or network. Node >= 22 with stripTypeScriptTypes.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'
import test from 'node:test'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const sourcePath = path.join(repo, 'nodejs/src/servers/grpc-stream-ingest-driver.ts')

function actualProductionDriver() {
    const source = readFileSync(sourcePath, 'utf8')
    const marker = 'export class GrpcStreamIngestDriver implements StreamIngestDriver {'
    assert.equal(source.split(marker).length, 2, 'the original production driver must exist exactly once')
    let actual = source.slice(source.indexOf(marker)).replace(marker, 'class GrpcStreamIngestDriver {')
    // Node strip-only mode cannot lower TS constructor parameter properties.
    // Rewrite ONLY the known TS sugar into equivalent JS assignment semantics.
    const ctor = `    constructor(
        private pipeline: GrpcIngestPipeline,
        private promiseScheduler: PromiseScheduler
    ) {}`
    assert.equal(actual.split(ctor).length, 2, 'the production driver constructor changed')
    actual = actual.replace(
        ctor,
        `    constructor(pipeline: GrpcIngestPipeline, promiseScheduler: PromiseScheduler) {
        this.pipeline = pipeline
        this.promiseScheduler = promiseScheduler
    }`
    )
    const compiled = stripTypeScriptTypes(actual, { mode: 'strip' })
    const deps = {
        Promise,
        createOkContext: (...args) => ({ args }),
        createKafkaDebugContext: (message) => ({ partition: message.partition, offset: message.offset }),
        deserializeKafkaMessage: (message) => ({ ...message, decoded: true }),
        budgetDeadline: (armedAt, softBudgetMs) => softBudgetMs === 0 || softBudgetMs >= 2 ** 31 ? null : armedAt + softBudgetMs,
        BatchBudget: {
            unlimited: () => ({ softAt: Infinity }),
            softDeadline: (softAt) => ({ softAt }),
        },
        isTimeoutResult: (result) => result?.kind === 'timeout',
    }
    const Driver = vm.runInNewContext(
        compiled + '\nGrpcStreamIngestDriver',
        deps,
        { filename: 'original-flind-grpc-stream-ingest-driver.js', timeout: 1000 }
    )
    assert.equal(typeof Driver, 'function')
    return Driver
}

const Driver = actualProductionDriver()
const deferred = () => {
    let resolve
    let reject
    const promise = new Promise((yes, no) => { resolve = yes; reject = no })
    return { promise, resolve, reject }
}
const scheduler = (waitForAll = async () => {}) => ({ waitForAll })
const item = (kind, offset) => ({
    result: { kind },
    context: { message: { partition: 7, offset } },
})
const pipelineResult = (elements, sideEffects = []) => ({
    elements,
    sideEffects,
    batchContext: { grpcStreamId: 41, grpcSeq: 3 },
})
const microtaskTurn = () => new Promise((resolve) => setImmediate(resolve))

test('production feed forwards decoded Kafka messages, stream identity, and anchored deadline', async () => {
    let observed
    const p = { feed: async (...args) => { observed = args; return { ok: true } } }
    const driver = new Driver(p, scheduler())
    const res = await driver.feed(41, 3, [{ partition: 7, offset: 29 }], { armedAt: 1000, softBudgetMs: 200 })
    assert.equal(res.ok, true)
    assert.equal(observed[0][0].args[0].message.decoded, true)
    assert.equal(observed[1].grpcStreamId, 41)
    assert.equal(observed[1].grpcSeq, 3)
    assert.equal(observed[2].softAt, 1200)
})

test('production driver has no phantom completed batch', async () => {
    const driver = new Driver({ next: async () => null }, scheduler())
    assert.equal(await driver.next(), null)
})

test('timeouts remain replayable; successful and dropped elements are accepted', async () => {
    const driver = new Driver({
        next: async () => pipelineResult([item('ok', 20), item('timeout', 21), item('drop', 22)]),
    }, scheduler())
    const result = await driver.next()
    assert.equal(result.streamId, 41)
    assert.equal(result.seq, 3)
    assert.equal(result.accepted, 2)
    assert.equal(result.unfinished.length, 1)
    assert.equal(result.unfinished[0].partition, 7)
    assert.equal(result.unfinished[0].offset, 21)
    await result.settled
})

test('settled barrier remains pending until side effects actually settle', async () => {
    const gate = deferred()
    let schedulerCalls = 0
    const driver = new Driver({
        next: async () => pipelineResult([item('ok', 20)], [gate.promise]),
    }, scheduler(async () => { schedulerCalls++ }))
    const { settled } = await driver.next()
    let complete = false
    void settled.then(() => { complete = true })
    await microtaskTurn()
    assert.equal(complete, false)
    assert.equal(schedulerCalls, 0)
    gate.resolve()
    await settled
    assert.equal(complete, true)
    assert.equal(schedulerCalls, 1)
})

test('settled barrier also waits for PromiseScheduler after batch side effects', async () => {
    const gate = deferred()
    const driver = new Driver({
        next: async () => pipelineResult([item('ok', 20)], [Promise.resolve()]),
    }, scheduler(() => gate.promise))
    const { settled } = await driver.next()
    let complete = false
    void settled.then(() => { complete = true })
    await microtaskTurn()
    assert.equal(complete, false)
    gate.resolve()
    await settled
    assert.equal(complete, true)
})

test('rejected side effect rejects the production settled barrier (no successful ACK)', async () => {
    const failure = Error('durable write failed')
    const driver = new Driver({
        next: async () => pipelineResult([item('ok', 20)], [Promise.reject(failure)]),
    }, scheduler())
    const { settled } = await driver.next()
    await assert.rejects(settled, /durable write failed/)
})

test('failed promise scheduler also rejects the production settled barrier', async () => {
    const driver = new Driver({
        next: async () => pipelineResult([item('ok', 20)], [Promise.resolve()]),
    }, scheduler(async () => { throw Error('async store drain failed') }))
    const { settled } = await driver.next()
    await assert.rejects(settled, /async store drain failed/)
})

test('zero and excessive allowances preserve the production unlimited-budget branch', async () => {
    const seen = []
    const driver = new Driver({ feed: async (_batch, _ctx, b) => { seen.push(b); return { ok: true } } }, scheduler())
    await driver.feed(1, 1, [], { armedAt: 500, softBudgetMs: 0 })
    await driver.feed(1, 2, [], { armedAt: 500, softBudgetMs: 2 ** 31 })
    assert.deepEqual(seen.map((x) => x.softAt), [Infinity, Infinity])
})
