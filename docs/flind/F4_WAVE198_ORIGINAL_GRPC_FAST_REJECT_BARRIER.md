# Flind Wave 198 — real HTTP/2 gRPC fail-closed on an already-rejected side effect

## Actual local integration PASS — 27 October 2026

**PASS:** Real loopback HTTP/2 gRPC connects the original first-party
`WorkerIngestServer`, `GrpcStreamIngestDriver`, and
`PromiseScheduler` (all directly staged from Git HEAD) using the
original generated Protobuf protocol.

The **test-only** in-memory pipeline schedules an already-rejected
synthetic disk-write Promise, explicitly waits until its pending Set
entry is removed, then supplies a completed batch with **no**
`sideEffects` in its result. This reproduces the exact race that
Wave197 repaired: without its persistent error envelope, the prior
`waitForAll()` would have returned successfully and ACKed the batch.

### Command and observed evidence

```bash
node tools/flind/qualify_production_grpc_fast_failure_wave198.mjs
```

The actual command returned **exit 0** (about 35 seconds) on macOS
with Node26, preexisting pinned local `esbuild`, Connect and Protobuf
dependencies. The qualifier stages **13 original Git files** into a
fresh marker-owned scratch directory, compiles their real classes,
connects a real HTTP/2 gRPC client, inspects replies and cleans its
scratch. No dependency download, package install or remote service.

Confirmed results:

- Original product gRPC server, original product driver and
  original product scheduler: **all executed**.
- Original product-generated Protobuf sent via loopback HTTP/2.
- Synthetic failure was already settled and **absent from pending Set**
  before the production driver's `waitForAll()` ran.
- No successful gRPC ACK was emitted.
- Client observed `Code.Internal` and the server reached its
  original fatal-error callback, with the synthetic failure reason.
- A subsequent gRPC connection was refused with `Code.Unavailable`.
- `production_joined_pipeline_qualified=false`,
  `durable_clickhouse_qualified=false`,
  `production_rust_consumer_qualified=false`,
  `release_qualified=false`.

**This is an actual original-class integration test with a synthetic
pipeline, not a complete production ingestion run.** Metrics/logger and
thin helper interfaces are test-only shims. The test does not write
to real ClickHouse, use a real Kafka broker, authenticate customers,
prove replay/dedup, or qualify the full original joined analytics
pipeline. Wave190–191 and Wave194 separately exercise real external
components under different test fixtures; the unbroken full product
path remains to qualify.

Private repository, GitHub Actions disabled, no release/deploy,
no paid compute and no customer data. Overall decision **NO-GO**.
