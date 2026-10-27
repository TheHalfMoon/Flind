# Flind Wave 200 — feed-order sentinel measures accepted batches only

## Production defect reproduced (27 October 2026)

Original `WorkerIngestServer.runReader()` executed
`feedOrderSentinel.check(...)` as soon as an inbound gRPC batch
was decoded, **before** the FIFO admission slot was acquired or the
pipeline was actually fed.

This causes the order sentinel's state to advance for unprocessed
batches which expire in the admission queue. The source invariant
explicitly says the sentinel measures the feed, not frame reception.
A later replay or offset check can therefore be measured against
a message that never entered the pipeline.

### Actual original-class red test

```bash
node tools/flind/qualify_grpc_accepted_only_feed_order_wave200.mjs
```

The qualifier stages original Flind source byte-for-byte from HEAD
(13 files) into a fresh owned scratch, uses preexisting offline
Node26 / Connect / Protobuf / esbuild dependencies, and operates the
**original** `WorkerIngestServer`, `GrpcStreamIngestDriver`, and
`FeedOrderSentinel` over two distinct **real loopback HTTP/2
streams**. Only the analytics pipeline and logging/helper interfaces
are test doubles.

The synthetic pipeline holds the only admission slot with a
synthetic side effect. Another stream with a 35 ms soft budget
receives a PARTIAL ACK with zero accepted and one unfinished
(replayable) offset **without ever entering the pipeline**.

Before the product fix, the verifier failed the actual assertion:

```
AssertionError: an admission-expired/never-fed message must NOT
advance actual product order sentinel
2 !== 1
```

Both stream batches were decoded, but **only one** was fed.

### Product correction

The original `feedOrderSentinel.check()` invocation now occurs
**inside the `if (result.ok)` branch**, after a driver feed has
been accepted and before the next batch is read. Expired admission
waits, cancelled streams, capacity retries, and feed rejections
therefore no longer register never-fed messages.

The original consumer incarnation/stream/assignment epoch
scope and replay status are preserved. No wire protocol, SDK,
stored event or Kafka offset format changes.

A regression assertion was also added to Flind's original
`grpc-server.test.ts` parked-budget test. The full Jest
workspace is not installed in this test environment; that
native Jest test's execution is **not claimed** here.

### Qualification limits

This integration runs original gRPC/server/driver/sentinel code,
but a synthetic processing pipeline; it does not establish the
complete joined analytics pipeline, native Kafka broker/consumer,
real ClickHouse production persistence or full frontend/backend.
No production deploy or release qualification.

Flind remains PRIVATE; GitHub Actions disabled; no package
downloads, paid models, publication or deployment. Release NO-GO.
