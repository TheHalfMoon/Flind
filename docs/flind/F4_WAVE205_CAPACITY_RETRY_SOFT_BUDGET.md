# Flind Wave 205 — enforce soft admission budget during gRPC capacity retries

## Original production defect

In the original `WorkerIngestServer.runReader()`, a sub-batch is
allowed into a FIFO admission slot and then passed to the original
`GrpcStreamIngestDriver`. If the pipeline returns `at_capacity`
despite the granted slot (capacity accounting drift), the server
retries indefinitely at `capacityRetryMs` intervals. The bounded
`softBudgetMs` timer is enforced only while the batch is waiting
for a FIFO slot, not during those post-grant capacity retries.

A client can therefore remain blocked beyond the soft admission
budget, preventing the next sub-batch on the same stream from being
read. This may retain capacity and postpone replay of unfed messages.

## Source-backed red → green evidence

```sh
node tools/flind/qualify_grpc_capacity_retry_budget_wave205.mjs
```

This test uses an actual local HTTP/2 gRPC/Protobuf roundtrip
with the original Flind production `WorkerIngestServer`,
`GrpcStreamIngestDriver`, `PromiseScheduler`, and
`FeedOrderSentinel` classes. A **synthetic** pipeline deliberately
returns `at_capacity` for offset 205. The first sub-batch has a
finite 40ms soft budget; a second sub-batch at offset 206 has no
budget and is accepted by the pipeline.

**Red evidence on Wave 204:** the test stopped after waiting 800ms,
rather than receiving the first sub-batch's PARTIAL response:

```
Error: capacity retry soft budget timed out after 800ms
```

## Production repair

The original server checks the same `softAt` deadline **after**
it holds a FIFO slot and **before** each attempted pipeline feed.
The `at_capacity` branch also expires the still-unfed sub-batch
when the deadline passes; otherwise it caps the sleep to the
remaining allowance.

Expiration emits the existing `PARTIAL` ACK with zero accepted
events and all original partition/offset coordinates marked as
unfinished. The FIFO slot is returned via the existing finally
block. The original request reader can then proceed to later
sub-batches on the same stream. A rejected attempt never advances
the accepted-feed order sentinel. Batches whose soft budget is
unlimited keep the previous capacity-retry behavior.

A native Jest regression is authored in
`nodejs/src/ingestion/api/grpc-server.test.ts`, but the full
native Jest runner was not installed or executed in this lean
environment; its execution is not claimed.

## Provenance and limitations

The qualifier checks clean Git HEAD source files and copies their
exact bytes into marker-owned temporary scratch before bundling
with existing offline Node 26, Connect, Protobuf and esbuild caches.
Only the pipeline, logger and Kafka context helper are test
doubles. The qualifier removes its owned scratch on completion.

This does **not** qualify the full production Rust Kafka consumer,
joined analytics pipeline, ClickHouse durability, Django auth,
tenant isolation, SDK/browser end-to-end, or full deployment/release
readiness. All test data is synthetic. The repository remains
PRIVATE; GitHub Actions remain disabled; no paid services, deploy
or publication. **Release NO-GO.**
