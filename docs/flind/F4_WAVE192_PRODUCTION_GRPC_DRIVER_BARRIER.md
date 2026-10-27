# Flind Wave 192 — original production gRPC driver acknowledgement barrier

## Scope and result — 27 October 2026

The Wave190–191 Kafka/Rust/Node/ClickHouse replay tests exercised Flind's real
Node WorkerIngestServer with a **test-only** StreamIngestDriver. This wave adds
an independently runnable, no-dependency check of the **original tracked
production** `GrpcStreamIngestDriver` from
`nodejs/src/servers/grpc-stream-ingest-driver.ts`.

Run:

```bash
node --test tools/flind/test_production_grpc_driver_wave192.mjs
```

Actual Mac local execution using Node 26.0.0: **8 tests, 8 pass, 0 fail**
(no downloads, paid services, customer data or network traffic).

The harness loads the tracked production TypeScript class and executes it in
a sandbox with mocked collaborators. Node's built-in type stripper cannot
handle TS constructor parameter properties, so the harness explicitly requires
an exact constructor source match and lowers **only that TypeScript syntax** to
equivalent JavaScript assignments. It rejects unexpected changes rather than
silently testing a reimplementation.

Verified behavior:
- Forwarding decoded Kafka messages and stream/sequence identity to `feed`.
- Anchored deadline forwarding and unlimited-budget branch.
- Empty pipeline completion returns `null` (no phantom ACK).
- Timed-out elements remain unfinished/replayable; handled ones are accepted.
- The settlement promise waits for batch side effects and the promise scheduler.
- Side-effect or scheduler rejection propagates as failed settlement.

Two matching Jest regression cases were also added to
`nodejs/src/servers/grpc-stream-ingest-driver.test.ts`. They must be executed
with the full Node dependency tree in a subsequent full-node qualification;
the isolated sparse worktree does not contain those dependencies.

## Qualification boundary

This proves **original production driver JavaScript control flow with
mocked dependencies**, not original production services working together.
It does **not** execute real `createJoinedIngestionPipeline`, Kafka group
rebalancing, authentication, deduplication, ClickHouse materialized views, or
SDK → API → Dashboard. No production exactly-once guarantee, no release gate
promotion, no external deployment. The original Wave191 real integration
receipt remains a separate and more extensive synthetic-only test.

Next qualification: wire the production `GrpcStreamIngestDriver` and its
joined ingestion pipeline to a real ClickHouse-backed test environment;
then verify Kafka replay/dedup, tenant isolation, and authenticated full-stack
E2E. Issue #82 and #5 remain open; **release NO-GO**. Repo private, no publish.
