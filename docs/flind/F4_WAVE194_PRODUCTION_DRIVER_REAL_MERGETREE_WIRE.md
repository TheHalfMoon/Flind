# Flind Wave 194 — original gRPC server + production driver + real MergeTree disk

## Actual macOS integration PASS — 27 October 2026

**Local Wave194 qualified exactly one source-backed, synthetic-only, real
ClickHouse durability boundary.** It extended Wave193's original
`WorkerIngestServer` + original `GrpcStreamIngestDriver` real HTTP/2
gRPC client/server with a test pipeline whose side effect actually writes
to official supported ClickHouse **25.12.7.21 MergeTree**, then opens that
disk store from an independent ClickHouse OS process.

Run:

```bash
node tools/flind/qualify_production_grpc_driver_mergetree_wave194.mjs
```

Observed result (exit 0, ~54s including source staging):
- Original first-party server and production driver: **true**.
- Original Protobuf over real loopback HTTP/2: **true**.
- Pinned, original official macOS ClickHouse asset SHA-256: **verified**.
- Supported ClickHouse 25.12.7.21 runtime: **verified**.
- Test-only pipeline inserted one synthetic event with team 101.
- A separate ClickHouse process read back the exact UUID, event,
  team, and synthetic distinct ID: **1 persisted row**.
- Actual gRPC ACK arrived **after** the disk readback.
- Actual gRPC response: **1 accepted, 1 unfinished/replayable offset 101**.
- 13 product source files staged directly from Git HEAD.
- Scratch isolated, marker-owned and cleaned. No model inference,
  package download, network deployment, customer data or paid service.

### What is real, and what is still test-only?

**Real:** original product gRPC server, original product
`GrpcStreamIngestDriver`, generated product Proto, HTTP/2 network
exchange, official ClickHouse executable, MergeTree disk persistence
and independent-process readback.

**Test-only:** the joined ingestion pipeline, its side-effect ordering
and SQL persistence implementation, plus narrow helper/logger shims.
This uses **neither** production ClickHouse ingestion/materialized views
**nor** production Kafka Rust ingester; the test-only pipeline supplies
the delayed side effect and timeout classification.

The result does not establish product exactly-once, dedup/replay safety,
multi-worker rebalance, broker restart, authentication, tenant isolation,
PostgreSQL migrations, or SDK→API→Dashboard E2E. Wave190/191 separately
qualify real Kafka→Rust→Node→ClickHouse with a *different* test driver.
The next substantial gap is combining both with the **original joined
production pipeline**, then exercising recovery and authenticated E2E.

**Release NO-GO.** #82 and #5 remain open. Flind stays PRIVATE with
Actions disabled. No publish, deploy, premium model, or actual user records.
