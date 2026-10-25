# Wave 92 — Kafka v1: wait for every batch and offset store before partition revoke

## Production defect

In the Node.js Kafka v1 consumer, the `ERR__REVOKE_PARTITIONS`
callback previously ran `Promise.all(backgroundTask.map(...))`
and called `completeRevocation(assignments)` after its first
rejection. As `Promise.all` rejects immediately when **any**
task fails, this could unassign Kafka partitions while other
event batches were still processing.

After the recent Wave88/89 offset-store fences, an additional
subtlety matters: a background task may already have been removed
from the active array while its ordered offset-store callback
has not yet completed. The old no-tasks fast path revoked
partitions immediately in that case.

## Implementation

- Add the dependency-light `awaitRevocationSafety(pending, gate)`
  coordinator. It first `await Promise.allSettled(pending)`,
  then `await gate.drain()`, and returns a bounded count of
  rejected tasks and whether the offset gate was poisoned.
- Snapshot in-flight tasks in the actual v1 rebalance callback
  and call the coordinator **even when the snapshot is empty**.
  A failed task no longer causes an early revoke; queued
  offset-store work must settle before `completeRevocation`.
- Preserve existing informational/error logging, record the
  failed-task count and gate state, handle drain or unassign
  failure, reset rebalance coordination on final cleanup error.
- Do not re-acknowledge failed work. The Wave88 permanent
  offset failure latch stays in force. Kafka's own partition
  management remains responsible for broker-level ownership.
- Kafka v2, SDK, ingestion handler, Kafka topic configuration,
  emitted events and schema remain untouched.

## Verification performed on October 25, 2026

- **6/6 isolated Node 22 runtime tests PASS** against the
  new actual TypeScript helper compiled with installed
  TypeScript: first/last batch failure, waiting for all
  batches, empty snapshot with pending gate, failed offset
  drain, healthy receipt, and multiple rejected batches.
- **Isolated `tsc --strict` PASS** for the new module.
- Added **6 Jest helper tests** and **2 callback-level Jest
  regressions** to the actual v1 mock-Kafka test suite.
- Added **4 dependency-free Python source guard tests**.
  Full private-repository Jest and a live Kafka rebalance run
  were **NOT EXECUTED** in this turn. The authorized Mac
  Remote Desktop Commander had reached its monthly usage
  limit; inherited GitHub Actions stay disabled.

## Safety and remaining release gates

This fixes the **local wait ordering** before v1 partition
unassignment. It is not proof of complete Kafka group
rebalance safety under real network partition, simultaneous
consumer failure, or broker-driven revoke deadlines. It does
not qualify full SDK capture → Kafka → production Rust/Node
ingester → ClickHouse → dashboard readback, complete Django
schema, frontend build, OAuth and tenant isolation, or E2E.

Keep Issue #82 OPEN and release status **NO-GO**.

Repository stays private; no deployments, publishing, paid
cloud, or changes to mandatory source LICENSE/NOTICE.
