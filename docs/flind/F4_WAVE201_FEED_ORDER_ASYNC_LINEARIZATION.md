# Flind Wave 201 — monitor accepted gRPC feeds in original invocation order

## Reproduced original production fault (27–28 October 2026)

After Wave200, Flind correctly excluded never-fed and rejected batches
from `FeedOrderSentinel`, but invoked the sentinel only **after**
`await feedGuarded(...)` resolved. Across simultaneous original gRPC
streams, independent `driver.feed()` promises may return in a
different order than calls entered the pipeline, so the diagnostic
would label an ordered Kafka feed as an offset regression.

Wave201's real loopback HTTP/2/Protobuf qualifier actually executes
the original Flind `WorkerIngestServer`, original
`GrpcStreamIngestDriver`, original `FeedOrderSentinel`, and original
`PromiseScheduler`, with an isolated **synthetic in-memory pipeline**.
The pipeline receives the same consumer incarnation, topic, partition
and Kafka key with offsets **300 then 301**, but deliberately resolves
the second feed's admission result **before** the first.

**Red on Wave200:** the qualifier exited nonzero:
```
AssertionError: monitor must linearize by the original feed
invocation order, not async result order
actual: [301, 300]
expected: [300, 301]
```

This is a falsified diagnostic order, not proof of event loss,
cross-tenant access, or a runtime bug in the Rust Kafka consumer.

## Product repair

The original `WorkerIngestServer` now:

1. Reserves a monotonic feed-order ticket **synchronously before**
   entering each asynchronous `driver.feed()` attempt.
2. Records whether that attempt was actually **accepted** or
   failed/rejected/temporarily at capacity.
3. Flushes completed tickets **only in original invocation order**;
   rejected and retry attempts advance the cursor without touching
   the original `FeedOrderSentinel`.
4. Preserves stream/assignment epochs, replay flags and the existing
   FIFO admission and processing ACK semantics.

The pending map retains at most currently unresolved feed attempts and
their reordered completions. Its entries are removed after the
corresponding order cursor advances. When no order sentinel is
configured, no tickets are allocated. No wire protocol, Kafka offset
or persisted event format changes.

## Reproducible tests

```bash
node tools/flind/qualify_grpc_feed_order_linearization_wave201.mjs

node --disable-warning=ExperimentalWarning --test \
  tools/flind/test_production_grpc_driver_wave192.mjs \
  tools/flind/test_joined_ingestion_group_key_wave195.mjs \
  tools/flind/test_feed_order_empty_kafka_key_wave196.mjs \
  tools/flind/test_promise_scheduler_fail_closed_wave197.mjs
```

The qualifier sources **13 exact original Git HEAD files** and uses
the pre-existing, locally cached Node/Connect/Protobuf/esbuild modules.
It rewrites no production methods in the fixture; only the synthetic
pipeline and helper/logger seams are test doubles. It creates and
removes only a marker-owned scratch folder.

A native Jest regression was also added to Flind's original
`nodejs/src/ingestion/api/grpc-server.test.ts`. The entire native
Jest workspace was not installed or executed in this lean environment,
so this Jest test is **authored, not fully run**.

## Qualification limits

The original production joined analytics pipeline, broker-managed
native Rust consumer, durable production ClickHouse writers,
Django/OAuth/tenant isolation, SDK-browser end-to-end and branding
gates remain unqualified. This isolated scenario exercises original
server/driver/sentinel behavior but **not** the complete production
ingestion stack.

Flind stays PRIVATE with GitHub Actions disabled. No publishing,
deployment, customer data, paid inference or paid dependencies.
Release **NO-GO**.
