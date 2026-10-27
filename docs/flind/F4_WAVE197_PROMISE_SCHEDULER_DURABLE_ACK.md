# Flind Wave 197 — fail-closed scheduler on already-rejected side effects

## Verified original production defect (27 October 2026)

Flind's `nodejs/src/common/utils/promise-scheduler.ts` originally
registered each scheduled side effect in a Set and removed the promise
from that Set when it resolved **or rejected**. The gRPC
`GrpcStreamIngestDriver.next()` waits for this scheduler's
`waitForAll()` as part of its ACK barrier.

If a side effect rejected and the cleanup microtask ran **before**
the driver's subsequent `waitForAll()`, the failed promise was
no longer in the snapshot. In that case `waitForAll()` resolved
even though an earlier scheduled side effect had already failed.
The exact timing was confirmed with an original-source test and
does not require actual ClickHouse to reproduce.

### Minimal production correction

`PromiseScheduler` now retains the **first rejected reason**,
including valid non-Error rejection values such as `undefined`,
inside a bounded single-record failure envelope. Each scheduled
promise is still cleaned from the Set on settlement; its original
return-value and tracking behavior is unchanged.

`waitForAll()` throws a remembered rejection both before taking the
next pending snapshot and after that snapshot resolves. The scheduler
remains **poisoned until recreated**, so subsequent ACK barriers cannot
silently succeed after a known failed durable side effect.
`waitForAllSettled()` retains its existing snapshot behavior.

### Actual tests

```bash
node --disable-warning=ExperimentalWarning --test \
  tools/flind/test_promise_scheduler_fail_closed_wave197.mjs \
  tools/flind/test_production_grpc_driver_wave192.mjs \
  tools/flind/test_joined_ingestion_group_key_wave195.mjs \
  tools/flind/test_feed_order_empty_kafka_key_wave196.mjs
```

Wave197 uses the **actual first-party TypeScript PromiseScheduler**
directly in Node 26, with no mocks, installations or network.
**Before repair: 2/6 PASS, 4/6 FAIL** — a fast rejection disappears,
later ACK waits incorrectly succeed, failure persistence is lost.
**After repair: 6/6 PASS**. Regression waves 192, 195, 196 yield
**23/23 PASS**, for **29/29 in total**. Two equivalent Jest
regression tests were also added to the existing production Node test
file but the full Jest workspace was not installed here, so the
full Jest suite has **not** been executed. Node syntax and Git diff
checks were run locally.

This change intentionally prefers a failed ingestion ACK rather than
acknowledging a known failed durable side effect. Any downstream
rebuild/restart of a poisoned worker and its Kafka offset replays
remain separate release qualifications.

## Remaining release gates

Production joined ingestion pipeline with full original dependencies,
native Rust consumer plus Kafka/ClickHouse under broker restart and
rebalance, persisted deduplication, Django/Auth/OAuth, independent tenant
isolation and SDK/browser E2E remain unqualified. No claim of global
exactly-once semantics or product release readiness is made.

Flind stays PRIVATE; no deploy, publish, paid service or actual
customer data. Overall release decision: NO-GO.
