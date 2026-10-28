# Flind Wave 204 — bounded HTTP/2 shutdown after drain

## Reproduced original server failure (28 October 2026)

The original `WorkerIngestServer.stop()` correctly drains accepted
pipeline batches and calls `session.close()` to send HTTP/2 GOAWAY.
However, `session.close()` waits for peer-initiated request streams
to finish. A client may leave an HTTP/2 request body open indefinitely.
The subsequent `http2Server.close()` then waits for that session and
can hang even though **no accepted batch remains**.

The source-backed test uses a real loopback TCP HTTP/2 client with an
unfinished POST request, without admitting any ingestion messages:

```bash
node tools/flind/qualify_grpc_idle_http2_shutdown_wave204.mjs
```

The initial isolated run passed due to transport timing, but the
repeat from the branch's committed source **reproduced the failure**
(the qualifier exited nonzero):

```
Error: original stop() hung on idle unfinished HTTP2 request
```

This is a shutdown/liveness issue, not an event corruption finding.

## Production correction

After the existing drain of accepted work and the normal response
ACK/failure handling, the original server still calls
`session.close()` for a graceful HTTP/2 GOAWAY. It now also attaches
a **500ms bounded grace timer** to each remaining session; if its
`close` event does not arrive in time, the session is destroyed.
The timer is unreferenced and cleared on normal closure.

This does **not** change batch admission, Kafka offsets, protobuf
frames, ACK settlement, consumer replay or durable writes. Because
the forced closure happens only **after** the existing batch-drain
phase, the normal accepted-batch settlement contract remains intact.
If that drain expires, the server already fails remaining work.

## Additional positive regression: concurrent shutdown

```bash
node tools/flind/qualify_grpc_shutdown_idempotence_wave204.mjs
```

The original server and driver are started, then concurrent
`Promise.all([server.stop(), server.stop()])` and another later
`stop()` resolve with no listener or stream remaining.
A matching regression test was added in the original native
`nodejs/src/ingestion/api/grpc-server.test.ts`.

## Provenance and qualification limits

Both qualifiers stage **13 original Flind source files exactly from
Git HEAD** into marker-owned scratch, bundle them with existing
offline Node26/Connect/Protobuf/esbuild dependencies and delete their
owned scratch. Test doubles are confined to the synthetic pipeline,
logger and Kafka context helper. The idle-session test uses an actual
HTTP/2 TCP connection but **not** fully formed gRPC protobuf frames
or an actual Rust worker.

The complete Jest workspace is not installed on this machine; the
new native Jest regression is authored, but its execution is not
claimed. Neither qualifier certifies the complete Rust/Kafka/Node
joined ingestion/ClickHouse path, Django/OAuth/tenant isolation,
SDK/browser E2E or full release readiness.

Flind remains PRIVATE; no paid services, downloads, GitHub Actions,
deployment or publication. **Release NO-GO**.
