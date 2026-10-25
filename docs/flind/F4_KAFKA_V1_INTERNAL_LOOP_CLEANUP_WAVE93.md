# Wave 93 — Kafka v1 consumer-loop cleanup after failed processing

## Why a second cleanup path needed repair

Wave 90 fixed the **public** `KafkaConsumer.disconnect()`
method. The internal v1 `startConsuming()` coroutine
still had a different early-shutdown path. It awaited
`Promise.all(this.backgroundTask.map(...))` at normal
exit and called `disconnectConsumer()` immediately
from its `finally` block.

If any batch failed, or if the loop itself threw after
a background task was created, the `finally` path could
disconnect Kafka while **other background tasks or queued
offset stores were still active**. A failure during cleanup
could also replace the original processing error.

## Implemented

- Add dependency-light `drainAndDisconnectConsumer`
  to wait for **all** background tasks using
  `Promise.allSettled`, then drain Wave88 ordered offset
  stores, and **always attempt** native broker disconnect.
- Preserve the original loop exception, all distinct
  rejected-task reasons and native disconnect failures
  without duplicate reasons. Rethrow one original error
  unchanged or `AggregateError` retaining multiple causes.
- Treat a poisoned offset gate as unsuccessful cleanup
  even when the background list has already become empty.
  Do not silently promote offset-store failures to success.
- Wire this helper into the **internal** v1 consume loop
  `finally` and stop using the fail-fast
  `Promise.all` there. Existing Kafka v2, SDK event
  format, broker configs and consumer offsets remain unchanged.
- Public `disconnect()` continues to use its Wave90
  safe cleanup routine and is not replaced in this wave.

## Executed evidence, October 25, 2026

- **8/8 actual isolated Node 22 runtime tests PASS** on
  the new TypeScript helper, compiled by installed
  TypeScript. Cases include delayed remaining batch after
  an early rejection, exact primary failure identity,
  background+disconnect dual failures, offset-gate drain
  failure with a still-attempted disconnect, clean shutdown,
  poisoned gate with zero pending batches, triple independent
  causes, duplicate cause elimination, and strict cleanup
  ordering. (The eight cases cover all these behaviors.)
- **Isolated `tsc --strict --noEmit` PASS** with the actual
  Wave88 gate type.
- Added **8 Jest helper regression tests** plus **4 Python
  source guards** to the repository for repeatability.
- The full private-repository Jest suite and a native
  Kafka v1 failure/shutdown integration test were **NOT
  RUN**, because the authorized Mac remote computer tool
  reached its monthly quota and inherited GitHub Actions
  are intentionally disabled.

## Explicit release scope

This is a bounded correction to the internal v1 cleanup
order, not proof of the production SDK→Kafka→Rust/Node
ingester→ClickHouse→dashboard path. The full Django schema
migrations, frontend production build, OAuth, tenant
authorization, browser E2E and release qualification are
still OPEN and the release remains **NO-GO**.

Keep Issue #82 open. Repository remains private with
inherited GitHub Actions disabled, no deployment or
publication, no paid cloud, and required legal
LICENSE/NOTICE source attribution untouched.
