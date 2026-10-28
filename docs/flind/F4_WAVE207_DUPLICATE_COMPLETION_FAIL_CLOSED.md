# Flind Wave 207 — fail closed on duplicate or unknown gRPC completion

## Production bug: an unaccepted result releases a FIFO slot

The original `WorkerIngestServer.settleAndAck()` invoked
`releaseAccepted()`, which silently returned if the
`streamId:seq` batch was not registered. **Regardless of that
result**, the server then called `slots.release()` and
`ackCompleted()`.

Consequently, if the shared processing pipeline returned an already
settled sub-batch *twice*, a duplicate completion granted extra
capacity beyond `maxConcurrentBatches`, and could emit duplicate
successful acknowledgements. This is a fail-open behavior under a
pipeline invariant violation.

## Source-backed red → green evidence

```sh
node tools/flind/qualify_grpc_duplicate_completion_wave207.mjs
```

The original Flind `WorkerIngestServer`,
`GrpcStreamIngestDriver` and `PromiseScheduler` are exercised
over **actual loopback HTTP/2 Connect gRPC / Protobuf**. The
**synthetic** in-memory pipeline deliberately emits the first
accepted batch's completion twice while a second batch is also
in flight. `maxConcurrentBatches` is set to two.

Before the product fix, the test failed with:

```
AssertionError: duplicate completion must not overflow the
configured FIFO capacity
```

## Product fix

`releaseAccepted()` now returns whether it actually released a
previously registered accepted batch. On success or failed
settlement, `settleAndAck()` only releases the corresponding
FIFO slot when that claim succeeds. For duplicate or unknown
completions, it calls the original shared pipeline fatal path
with a fixed, non-sensitive error and returns **without a second
slot release or ACK**. The client must replay any unacknowledged
tail and the owner must rebuild its poisoned pipeline, preserving
the existing fail-closed contract.

The test does **not** claim that the production batching pipeline
normally emits duplicate completions. It proves that this invalid
downstream result can no longer create additional admission
capacity or silently acknowledge replayable offsets.

A native Jest regression is authored in
`nodejs/src/ingestion/api/grpc-server.test.ts`. Its full suite
is not claimed executed: the cached scratch Jest launcher currently
references a missing `pnpm` package path, so it exits before
loading tests. The scratch overlay qualification restored every
overlaid source and left the user's worktrees unchanged.

## Limits

The test stages 13 original Flind first-party sources from Git HEAD,
verifies their bytes, uses only locally cached dependencies,
and removes marker-owned scratch. The pipeline, logging and Kafka
context helper are explicitly synthetic/test-only. No actual
Kafka/Rust consumer, joined analytics pipeline, durable ClickHouse,
Django tenancy/auth or browser end-to-end is qualified here.

Repository PRIVATE; Actions disabled; no downloads, cloud,
paid services, deployment or publication. **Release NO-GO.**
