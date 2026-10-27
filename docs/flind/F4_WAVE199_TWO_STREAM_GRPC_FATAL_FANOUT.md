# Flind Wave 199 — production gRPC fatal failure across two live streams

## Actual integration PASS — 27 October 2026

Original Flind `WorkerIngestServer`, `GrpcStreamIngestDriver`, and
`PromiseScheduler` were loaded from **13 Git-staged source files** and
executed over two simultaneous loopback HTTP/2 gRPC streams using the
original generated Protobuf protocol.

A **synthetic** in-memory test pipeline admitted **two** batches into
distinct live streams, then scheduled one synthetic durable-write
rejection in the real shared scheduler. The rejection's original pending
Set entry was removed **before** the original driver's ACK barrier
executed. The driver rejected settlement, and the original server
poisoned/fatalled both live streams rather than ACKing one and leaving
another apparently healthy.

### Exact executed command

```bash
node tools/flind/qualify_production_grpc_two_stream_fatal_wave199.mjs
```

Actual exit code **0**, about 39 seconds on the local Mac with Node26
and already-installed pinned `esbuild`/Connect/Protobuf. The test
stages first-party source from Git HEAD into marker-owned disposable
scratch. It uses no user data, package download, paid service or
external network. The qualifier cleaned only its owned scratch.

Confirmed runtime evidence:

- Original first-party server, original gRPC driver and original
  shared scheduler were all actually executed.
- **Two** separate actual HTTP/2 streams exchanged original protobuf
  messages; both synthetic batches were received by the test pipeline
  before failure.
- The synthetic rejection was removed from the pending Set *before*
  `waitForAll`; the real Wave197 scheduler still remembered it.
- **Neither stream received a successful ACK.**
- Both clients received real gRPC `Code.Internal`.
- A subsequent third stream received `Code.Unavailable` because the
  original server had been poisoned.
- No production joined analytics pipeline was executed. No Kafka,
  ClickHouse or original Rust consumer was used in this particular test.

### Scope and release gates

This qualifies failure propagation in an **original production
server/driver/scheduler combination**, not the durability of the
full actual ingestion application. The upstream pipeline, helper
interfaces and logger are narrow test fixtures. Cross-stream fatal
propagation is not proof of broker rebalance correctness, deduplication,
exactly-once behavior, authenticated tenant isolation, supported
Django startup, or SDK-to-dashboard E2E.

Flind remains PRIVATE, without GitHub Actions, release, publication,
deployment, customer data or paid inference. **Release NO-GO.**
