# Wave 124 — Lossless Protobuf int64 admission at production Node WorkerIngest boundary

## Production correctness defect

The first-party production `nodejs/src/ingestion/api/grpc-server.ts::grpcMessageToSerialized` converted Kafka `offset` and `timestamp` directly using `Number(message.offset)` and `Number(message.timestamp)`. The original first-party WorkerIngest Protobuf declares both values as `int64`, decoded in Node as `bigint`.

JavaScript `Number` cannot exactly represent all 64-bit integers. Example `9007199254740993n` silently rounds to `9007199254740992`; a rounded Kafka **offset** can corrupt the position used for ordering, replay and commit decisions. This is an edge case unlikely at ordinary current Kafka offsets but a real correctness fault that must fail safely, not silently mutate metadata.

## Product change

Moved the existing gRPC-to-Node Kafka adapter into `nodejs/src/ingestion/api/grpc-message-converter.ts`, with two **type-only** imports (no external runtime dependencies), and retained the original `grpc-server.ts` exported function as a re-export for compatibility. `grpc-server.ts` continues using that same production converter for each incoming `subBatch.messages`.

Both `offset` and `timestamp` use a checked conversion: require `Number.isSafeInteger(asNumber)` and exact `BigInt(asNumber) === original bigint`; otherwise throw a `RangeError`, causing the surrounding gRPC stream to fail closed instead of feeding corrupted coordinates to the production worker. Valid positive/negative safe integers, regular event data, Unicode, headers, and the Kafka distinction between empty string and null tombstone remain unchanged.

**No changes** to Kafka headers/wire formats, gRPC Protobuf schema, persisted ClickHouse tables, Kafka commit or ACK protocol, external services, legally required third-party notices, or deployment.

## Actual tests — October 26, 2026

On the user's Mac, using the existing **Node v26** native TypeScript type stripping and without a full pnpm workspace installation:

```sh
node --no-warnings --experimental-strip-types --test \
  tools/flind/test_node_grpc_int64_wave124.mjs
python3 -m unittest -q tools.flind.test_node_grpc_int64_source_wave124
```

- **10/10 actual production TypeScript converter function tests PASS**: regular Kafka gRPC event metadata; empty key/value retained; null tombstone retained; safe integer boundaries; positive and negative unsafe offset rejection; unsafe timestamp rejection; safe negative and zero timestamps; no input mutation; Unicode event data.
- **5/5 integration/source guard tests PASS**: the actual gRPC server imports, re-exports and uses this adapter for every incoming sub-batch; original Protobuf `int64` contract; fail-closed exact-conversion guard and type-only import; original Jest regression tests included.
- Added `nodejs/src/ingestion/api/grpc-message-converter.test.ts` to the existing project's Jest suite, with the same safe/unsafe boundary cases. **The Jest test file has NOT been run** because the full locked `node_modules` dependency closure is missing on the Mac; the native Node tests execute the actual production function, not a rewritten version.
- Node syntax and Python compilation checks, and Git whitespace checks pass. Mac retained ~12 GiB available.

## Release qualification boundary

This is a real production **Node worker edge correctness repair** with direct execution of the first-party converter; it does **not** mean the full production `nodejs/src/ingestion` worker has booted, gRPC has processed real end-to-end data through Node, events are in durable product ClickHouse tables, or authenticated tenant API and dashboard/browser are qualified.

Keep Issue #82 OPEN, Flind release NO-GO, repository private, inherited Actions disabled, no paid/cloud deployment, required legal attribution intact.
