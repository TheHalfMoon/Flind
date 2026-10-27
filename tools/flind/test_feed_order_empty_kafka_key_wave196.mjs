#!/usr/bin/env node
// Execute the real Flind FeedOrderSentinel from TypeScript, with only metrics
// and logging replaced by non-networking test doubles. No product rewrite.
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import vm from 'node:vm'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const original = path.join(root, 'nodejs/src/ingestion/api/feed-order-sentinel.ts')
const converter = path.join(root, 'nodejs/src/ingestion/api/grpc-message-converter.ts')
const source = readFileSync(original, 'utf8')
assert.match(source, /export class FeedOrderSentinel/)
const deps = [
  path.join(root, 'nodejs/node_modules/esbuild/package.json'),
  '/private/tmp/flind-wave186-grpc-core/node_modules/esbuild/package.json',
].find(existsSync)
assert.ok(deps, 'preinstalled esbuild required; this test never installs dependencies')
const esbuild = createRequire(deps)('esbuild')
const stub = [
  'export class Counter { inc() {} }',
  'export class Gauge { inc() {} dec() {} set() {} }',
].join('\n')
const result = await esbuild.build({
  stdin: {
    contents: 'export { FeedOrderSentinel } from ' + JSON.stringify(original) + ';\n' +
      'export { grpcMessageToSerialized } from ' + JSON.stringify(converter) + ';',
    sourcefile: 'flind-wave196-original-module-entry.ts', resolveDir: root, loader: 'ts',
  },
  bundle: true, write: false, format: 'cjs', platform: 'node',
  target: 'node26', logLevel: 'silent',
  plugins: [{
    name: 'flind-wave196-isolated-metrics',
    setup(build) {
      build.onResolve({ filter: /^prom-client$/ }, () => ({ path: 'metrics', namespace: 'wave196' }))
      build.onLoad({ filter: /.*/, namespace: 'wave196' }, () => ({ contents: stub, loader: 'js' }))
      build.onResolve({ filter: /^~\/common\/utils\/logger$/ },
        () => ({ path: 'logger', namespace: 'wave196-log' }))
      build.onLoad({ filter: /.*/, namespace: 'wave196-log' },
        () => ({ contents: 'export const logger={warn(){}}', loader: 'js' }))
    },
  }],
})
const mod = { exports: {} }
vm.runInNewContext(result.outputFiles[0].text, {
  module: mod, exports: mod.exports,
}, { filename: 'actual-Flind-feed-order-sentinel.cjs', timeout: 1000 })
const { FeedOrderSentinel, grpcMessageToSerialized } = mod.exports
assert.equal(typeof grpcMessageToSerialized, 'function')
assert.equal(typeof FeedOrderSentinel, 'function')
const message = (key, offset, topic = 'synthetic', partition = 0) => ({
  key, offset, topic, partition,
})
const check = (sentinel, messages, consumerId = 'flind-wave196', replay = false) =>
  sentinel.check(messages, consumerId, replay)
const counts = result => ({ outOfOrder: result.outOfOrder, replayed: result.replayed })

test('empty Kafka key must be treated as a keyed routing identity', () => {
  const sentinel = new FeedOrderSentinel()
  assert.deepEqual(counts(check(sentinel, [message('', 15)])), { outOfOrder: 0, replayed: 0 })
  assert.equal(sentinel.size, 1)
  assert.deepEqual(counts(check(sentinel, [message('', 14)])), { outOfOrder: 1, replayed: 0 })
  assert.equal(sentinel.size, 1)
})

test('empty Kafka key replay is counted without an out-of-order violation', () => {
  const sentinel = new FeedOrderSentinel()
  check(sentinel, [message('', 15)])
  assert.deepEqual(counts(check(sentinel, [message('', 14)], 'flind-wave196', true)),
    { outOfOrder: 0, replayed: 1 })
})

test('original gRPC converter preserves zero-byte Kafka key for order checking', () => {
  const proto = {
    topic: 'synthetic', partition: 0, offset: 19n, timestamp: 1761500000000n,
    key: '', value: '{"event":"$pageview"}', headers: {},
  }
  const decoded = grpcMessageToSerialized(proto)
  assert.equal(decoded.key, '')
  assert.equal(decoded.offset, 19)
  const sentinel = new FeedOrderSentinel()
  check(sentinel, [decoded])
  assert.deepEqual(counts(check(sentinel, [{ ...decoded, offset: 18 }])),
    { outOfOrder: 1, replayed: 0 })
})

test('null routing key remains an unkeyed record', () => {
  const sentinel = new FeedOrderSentinel()
  assert.deepEqual(counts(check(sentinel, [message(null, 10), message(null, 9)])),
    { outOfOrder: 0, replayed: 0 })
  assert.equal(sentinel.size, 0)
})

test('empty-string key is distinct from a nonempty key', () => {
  const sentinel = new FeedOrderSentinel()
  check(sentinel, [message('', 20), message('x', 10)])
  assert.equal(sentinel.size, 2)
  assert.deepEqual(counts(check(sentinel, [message('x', 11), message('', 21)])),
    { outOfOrder: 0, replayed: 0 })
})

test('empty-string key retains independent topic and partition coordinates', () => {
  const sentinel = new FeedOrderSentinel()
  check(sentinel, [message('', 20, 'topic-a', 0)])
  assert.deepEqual(counts(check(sentinel, [
    message('', 10, 'topic-a', 1), message('', 10, 'topic-b', 0),
  ])), { outOfOrder: 0, replayed: 0 })
  assert.equal(sentinel.size, 3)
})

test('consumer incarnation handoff rebaselines an empty Kafka key', () => {
  const sentinel = new FeedOrderSentinel()
  check(sentinel, [message('', 20)], 'old-consumer')
  assert.deepEqual(counts(check(sentinel, [message('', 19)], 'new-consumer')),
    { outOfOrder: 0, replayed: 0 })
  assert.deepEqual(counts(check(sentinel, [message('', 18)], 'new-consumer')),
    { outOfOrder: 1, replayed: 0 })
})

test('empty-key LRU respects bounded maximum keys', () => {
  const sentinel = new FeedOrderSentinel(1)
  check(sentinel, [message('', 20)])
  check(sentinel, [message('other', 10)])
  assert.equal(sentinel.size, 1)
  assert.deepEqual(counts(check(sentinel, [message('', 19)])),
    { outOfOrder: 0, replayed: 0 })
})
