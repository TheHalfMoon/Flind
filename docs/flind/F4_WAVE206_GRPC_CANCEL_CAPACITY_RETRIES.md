# Flind Wave 206 — cancel accepted-slot capacity retries on disconnect

## Original defect reproduced on Flind first-party gRPC source

The production `WorkerIngestServer.runReader()` correctly aborts a
**queued** `FifoSlots.acquire()` on disconnect, but once a FIFO slot
has been granted its `at_capacity` retry loop only checks for
`draining`, `fatalError` and finite soft-budget expiry. A cancelled
consumer with **unlimited** `softBudgetMs = 0` can thus retain an
admission slot indefinitely and continue calling `driver.feed()`
even after its live HTTP/2 client disappears.

### Repro: red on Wave 205

```sh
node tools/flind/qualify_grpc_cancel_during_capacity_retry_wave206.mjs
```

The qualifier uses an actual loopback HTTP/2, Connect gRPC and
protobuf client with the **original** `WorkerIngestServer`,
`GrpcStreamIngestDriver` and `PromiseScheduler`. The original
production driver feeds synthetic messages into an explicitly
synthetic in-memory pipeline that returns `at_capacity` forever.
Once multiple retries have occurred, the actual client cancels
the RPC via `AbortController`.

The pre-fix run failed:

```
Error: timeout waiting for cancelled stream releases FIFO slot
```

This is a capacity retention / availability defect, not proof of
event data loss. No event was accepted during the test.

### Production fix

The original post-admission retry loop now also checks the server
handler's client `AbortSignal` **before every new attempt**. On
disconnect, it calls the existing `finishReader(stream, seq)`
and returns. The existing `try/finally` releases its acquired
FIFO admission slot if nothing was accepted.

This preserves all original settlement rules: if a previous
`feed()` was actually accepted, its record still belongs to
the pump and must settle; the fix does not ACK disconnected
consumers, synthesize an accepted feed, or move the watermark
of the original `FeedOrderSentinel`.

A native Jest regression is added to
`nodejs/src/ingestion/api/grpc-server.test.ts`. The complete
Jest workspace is not present in the lightweight local environment,
so this native test is **authored but not claimed executed**.

### Qualification scope and constraints

The source-backed qualifier bundles 13 original Flind product
sources exactly matching clean Git HEAD, and uses cached local
Node26/Connect/Protobuf/esbuild packages. Test-only shims are
limited to the logging/context helpers and synthetic pipeline.
No production Rust Kafka consumer, joined analytics pipeline or
ClickHouse persistence is involved.

Remaining release gates include original Rust/Kafka/Node joined
analytics/ClickHouse E2E, Django/auth and tenant isolation,
SDK/browser E2E, full native Jest and product acceptance.
The repo remains PRIVATE, GitHub Actions stay disabled,
and no paid services, releases or deployments occur.
**Release NO-GO.**
