# Flind Wave 209 — Wait for acceptance before settling an early gRPC completion

## Reproduced product race

The original `WorkerIngestServer.runReader()` registers an accepted
batch only **after** its asynchronous `driver.feed()` call resolves
`{ ok: true }`. A concurrent stream can wake the shared completion pump
while another stream's pipeline feed has already placed a valid
completion on `next()` but its `feed()` promise has not yet
resolved.

Wave207 appropriately rejected duplicate/unknown completions, but
its strict `releaseAccepted()` check did not distinguish a
**legitimate early completion with acceptance still pending** from
an unknown/duplicate result. This can trigger a false pipeline
fatal and unnecessarily replay work after healthy processing.

## Original-source reproduction

```sh
node tools/flind/qualify_grpc_early_completion_wave209.mjs
```

The original Flind server, `GrpcStreamIngestDriver`,
`PromiseScheduler`, `FeedOrderSentinel`, protobuf types and
two real loopback HTTP/2 Connect gRPC streaming clients are used.
The **synthetic** in-memory pipeline emits a completed batch for
offset 209, holds the first `feed()` resolution, and accepts a
separate client batch for offset 210, waking the original shared
pump while the first registration is still pending.

**RED on Wave208:** the actual RPC failed with

```
ConnectError: [internal] ingest pipeline failed
```

The test does not prove that this race occurs under the full
joined production pipeline in ordinary load; it demonstrates
that the original pipeline-driver interface permits this
asynchronous ordering and that the original server handled it
unsafely.

## Repair

Before calling an asynchronous pipeline `feed()` after a FIFO
admission grant, the original server records a **per-batch
`streamId:seq` admission barrier**. Its `finally` removes that
barrier and resolves it only after registering accepted results
or determining rejection. The pump waits for that specific
in-progress acceptance before releasing a completion's
admission slot or issuing an ACK.

The acceptance barrier does **not** grant a batch admission or
mark it successful: duplicate or unknown completions still
fail closed with Wave207's existing slot and ACK protections.
Rejected/aborted batches still release their acquired FIFO
slots. The accepted pipeline's side-effect settlement barrier
is unchanged, and no client receives ACKs before acceptance
and side-effect settlement.

A native Jest regression is added in
`nodejs/src/ingestion/api/grpc-server.test.ts` but is authored,
not executed in this lightweight environment. Node Jest
dependencies are missing from the strictly offline pnpm cache,
as independently established in Wave208.

## Limits

The source-backed qualification stages 13 exact first-party
source files attested against Git HEAD. Helpers and the
in-memory pipeline are test doubles. No original full
Rust/Kafka/Node joined ingestion, durable ClickHouse,
Django/tenant/auth, browser/SDK end-to-end, or full native
Jest qualification is claimed.

Repository PRIVATE, GitHub Actions disabled, no deployment,
publication, paid services, or new downloads. **Release NO-GO.**
