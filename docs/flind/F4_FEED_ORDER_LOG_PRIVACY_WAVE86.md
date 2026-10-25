# Wave 86 — Production ingestion ordering diagnostics: redact Kafka keys

## Actual production-path defect

The Node.js ingestion worker's `FeedOrderSentinel` is invoked before
feeding messages into the pipeline sent by the Rust Kafka consumer.
The diagnostic warning previously serialized its internal
`topic/partition/key` identity into operational logs. Actual Flind
ingestion fixtures use Kafka routing keys derived from
`token:distinct_id`. Consequently, when an out-of-order event is
observed, the log may expose a capture API token, a distinct user
identifier, or both.

An unrelated, defensive correctness issue: separating topic,
partition and key with unescaped slash characters yields an
ambiguous internal identity for certain unexpected upstream string
tuples. Even though normal Kafka topic names reject slashes,
unambiguous encoding is the correct boundary for the worker's
incoming serialized data.

## Implementation

- Replace the internal delimiter-concatenated identity with the
  unambiguous `JSON.stringify([topic, partition, key])` tuple.
  The original key remains inside the bounded process-local LRU,
  not in log fields.
- Emit only topic, partition, current/previous offsets and consumer
  incarnation in the out-of-order warning. Never emit `message.key`
  or the combined token/distinct-id.
- Preserve existing counter names, gauges, offset/replay logic,
  eviction behavior and output schema.
- Add Jest regressions for distinct topic/partition/key identities
  that would have collided under slash concatenation and for a
  deliberately sensitive capture-key warning.
- Add two stdlib source guardrails against restoration of the
  ambiguous key or raw Kafka key in warning attributes.

## Verification performed, 2026-10-25

- **7/7 isolated TypeScript-transpiled sentinel behavior checks PASS**
  locally under Node 22 with mocked Prometheus/log dependencies;
  checks include ordered events, violations, legitimate replay,
  consumer restart rebaseline, previously colliding identities,
  no raw capture token or distinct ID in warnings, LRU bounds and
  unkeyed events.
- **2/2 Python source-guard tests PASS** on the locally reconstructed
  patch, checking the exact identity and warning metadata contracts.
- The full repository Jest suite and native Rust->gRPC->Node ingestion
  services **were not run** in this turn. Remote Desktop Commander
  for the authorized Mac reported its monthly tool limit; the
  device remains connected and must not be retried/reconnected.
- The new Jest tests are committed for repeatable verification when
  the Node.js repository test environment is available.

## What this does not qualify

This is a narrow live-worker diagnostics and privacy fix, not
proof of ingestion through production SDK capture, Kafka,
ClickHouse materialized views and the Flind dashboard. It does
not remove original source attribution or rename compatibility
API identifiers. Full Django migrations, frontend build, browser
E2E, OAuth/tenant boundary and release gates remain **NO-GO**.

Repo remains private; inherited Actions stay disabled. No
publication, deployment or paid service.

When Node.js dependencies are provisioned, rerun:

`pnpm --filter @flind/nodejs exec jest --runInBand --runTestsByPath src/ingestion/api/feed-order-sentinel.test.ts`

And the dependency-free guard:

`python3 -m unittest tools.flind.test_feed_order_privacy_wave86 -q`
