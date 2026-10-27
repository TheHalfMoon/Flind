#!/usr/bin/env node
// Wave197 executes ORIGINAL Flind PromiseScheduler TypeScript with Node's
// built-in TypeScript support. No mocks or imported npm packages.
import assert from 'node:assert/strict'
import test from 'node:test'
import { PromiseScheduler } from '../../nodejs/src/common/utils/promise-scheduler.ts'

test('a failed, already-cleared side effect must still fail the later ACK barrier', async () => {
  const scheduler = new PromiseScheduler()
  const error = new Error('synthetic ClickHouse write rejected')
  const rejected = Promise.reject(error)
  assert.equal(scheduler.schedule(rejected), rejected)
  await rejected.catch(() => {})
  await Promise.resolve()
  assert.equal(scheduler.promises.size, 0, 'fast rejected promise has left the pending set')
  await assert.rejects(scheduler.waitForAll(), /synthetic ClickHouse write rejected/)
})

test('a delayed failed side effect must fail concurrent ACK barriers', async () => {
  const scheduler = new PromiseScheduler()
  const rejected = Promise.reject(new Error('synthetic materialization failed'))
  scheduler.schedule(rejected)
  await rejected.catch(() => {})
  await Promise.resolve()
  await assert.rejects(scheduler.waitForAll(), /synthetic materialization failed/)
  await assert.rejects(scheduler.waitForAll(), /synthetic materialization failed/)
})

test('successful scheduled work retains existing value and cleanup semantics', async () => {
  const scheduler = new PromiseScheduler()
  let resolve
  const pending = new Promise(r => { resolve = r })
  assert.equal(scheduler.schedule(pending), pending)
  assert.equal(scheduler.promises.size, 1)
  const waiting = scheduler.waitForAll()
  resolve('persisted')
  assert.deepEqual(await waiting, ['persisted'])
  await Promise.resolve()
  assert.equal(scheduler.promises.size, 0)
  assert.deepEqual(await scheduler.waitForAll(), [])
})

test('failure while a wait is in progress fails that wait and every later wait', async () => {
  const scheduler = new PromiseScheduler()
  let reject
  const pending = new Promise((_, r) => { reject = r })
  scheduler.schedule(pending)
  const waiting = scheduler.waitForAll()
  reject(new Error('synthetic durable receipt failed'))
  await pending.catch(() => {})
  await assert.rejects(waiting, /synthetic durable receipt failed/)
  await assert.rejects(scheduler.waitForAll(), /synthetic durable receipt failed/)
})

test('a previously failed side effect is not hidden by a later successful one', async () => {
  const scheduler = new PromiseScheduler()
  const failed = Promise.reject(new Error('persistent failure'))
  scheduler.schedule(failed)
  await failed.catch(() => {})
  await Promise.resolve()
  await scheduler.schedule(Promise.resolve('ok'))
  await assert.rejects(scheduler.waitForAll(), /persistent failure/)
})

test('waitForAllSettled still returns settled results for currently pending promises', async () => {
  const scheduler = new PromiseScheduler()
  let resolve
  const pending = new Promise(r => { resolve = r })
  scheduler.schedule(pending)
  const waiting = scheduler.waitForAllSettled()
  resolve('success')
  const results = await waiting
  assert.equal(results.length, 1)
  assert.deepEqual(results[0], { status: 'fulfilled', value: 'success' })
})
