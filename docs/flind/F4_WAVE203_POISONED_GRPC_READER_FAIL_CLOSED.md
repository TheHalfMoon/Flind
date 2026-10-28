# Flind Wave 203 — fail closed in already-open gRPC request readers

## Original product defect reproduced (28 October 2026)

The original `WorkerIngestServer.fatal()` poisons the pipeline, calls
`onFatal` and fails every response stream. It previously did **not**
stop the independent `runReader()` loop on an existing session.
A request iterator can outlive the response iterator, so a peer could
still submit another batch after the failure, before process shutdown
completed. A new stream was already rejected; this gap concerned
**existing** readers.

### Source-backed red evidence

```bash
node tools/flind/qualify_grpc_poisoned_reader_wave203.mjs
```

Actual original server, `GrpcStreamIngestDriver` and
`PromiseScheduler`, staged byte-for-byte from 13 Git HEAD sources,
were run with a **synthetic** in-memory pipeline and the original
server's streaming request-generator API. The first synthetic batch
at offset 203 schedules a rejected write, the original pump announces
fatal and the stream reports `Code.Internal`. The test sends a second
frame at offset 204 **over the already-running reader**, after poison.

Before the fix the actual assertion failed:

```
AssertionError: poisoned original live request reader must not
feed the second batch
actual: [203, 204]
expected: [203]
```

This directly proves the former application-level hole; it does **not**
claim proof of HTTP/2 transport disconnect behavior. The real
production joined analytics pipeline, Kafka broker and ClickHouse
are not involved in this focused test.

### Product correction

The original `runReader()` now stops on `fatalError` as well as
draining when it reads another frame; its capacity/retry loop also
checks `fatalError`, and `feedGuarded()` checks poison immediately
before a new driver call. The existing `fatal()` response queue
failure and the onFatal owner callback remain unchanged.

No new events are fed after the fatal signal, even if an old reader
briefly survives its response stream. Already-accepted work retains
the existing Wave202 orphan-drain contract; no changes to Kafka
offsets, ACK framing, serialization or credentials.

A native regression is also written into the original
`nodejs/src/ingestion/api/grpc-server.test.ts` using the real
server and existing FakeDriver. This lightweight machine does not
have the full native Jest workspace installed; the authored Jest test
is **not** claimed executed. Tests using the actual source-backed
qualifier cover the defect.

### Boundaries and release state

This proves behavior of original source-backed classes, not full
end-to-end Rust/Kafka/Node/ClickHouse, Django/OAuth/tenant isolation,
SDK/browser or commercial release readiness.

The Flind repository remains PRIVATE, GitHub Actions disabled,
no releases, paid model calls, deployment or user data.
**Release NO-GO.**
