# Flind Wave 208 — Bound queued gRPC acknowledgements for non-reading clients

## Product issue reproduced on original WorkerIngestServer

The original `AckQueue` kept an **unbounded** `items` array of
responses waiting for an individual streaming gRPC consumer.

Normally the FIFO admission slots limit accepted pipeline batches.
However, an empty `subBatch.messages` is acknowledged directly
without entering pipeline admission. A consumer sending many empty
sub-batches while not consuming responses could force the original
server to enqueue one ACK per frame with no per-stream bound.

The source-backed Wave208 regression uses the original
`WorkerIngestServer` and generated protobuf types. An in-memory
async request iterable supplies 320 correctly sequenced **empty**
sub-batches after the `hello` frame, while the response generator
deliberately stops reading after the initial `ready` frame.

**RED on Wave207:** the test rejected the original `AckQueue`
because its unread response queue exceeded 256 items:

```text
AssertionError: empty-batch ACKs must not grow the original
response queue beyond its bound
```

The test specifically does **not** claim to use an HTTP/2 transport
or to prove any durable Kafka/ClickHouse behavior.

## Product correction

Set a conservative bounded backlog of **256 response frames per
stream**. When more responses are queued and the peer is not
consuming them, `AckQueue.push()` marks only that stream as failed
with gRPC `ResourceExhausted`. The original request reader stops
admitting more frames, including the empty-batch fast path.

The server does **not** poison the shared pipeline on a slow peer
and does not turn unaccepted batches into successful ACKs. Accepted
work still settles under the normal pump and FIFO-slot ownership
rules. Unacknowledged messages must be replayed by the consumer on
a subsequent connection. The bound contains memory use even if
the peer does not immediately notice its failed stream.

A native Jest regression was authored in
`nodejs/src/ingestion/api/grpc-server.test.ts`. It deliberately
does not consume responses until the bounded rejection is observed.

## Local environment and qualification limitations

The original four-suite Jest runner remains **blocked** rather than
treated as passing. A real local pnpm 11.28.5 and a 5.6GB content
store were found, but a strictly `--offline --frozen-lockfile
--ignore-scripts` install into the isolated Wave208 worktree
reported `ERR_PNPM_NO_OFFLINE_TARBALL` on necessary packages.
No internet downloads, paid services, or global package mutations
were authorized or attempted. Previous stale Jest executable
pointed to a missing PNPM package path. Full native Jest remains
unexecuted.

The Wave208 qualification bundles original Flind product source
bytes from a clean Git HEAD and uses only pre-cached
Node26/Protobuf/Connect/esbuild packages with synthetic helpers.
It does not certify full HTTP/2 handling, the production joined
analytics pipeline, original Rust/Kafka consumer, durable
ClickHouse, Django auth/tenant isolation, or browser/SDK E2E.

The repository remains PRIVATE with Actions disabled.
**Release NO-GO**. No deployment or publication.
