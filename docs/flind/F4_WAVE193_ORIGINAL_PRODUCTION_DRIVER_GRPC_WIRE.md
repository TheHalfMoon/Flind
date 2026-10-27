# Flind Wave 193 — original production gRPC driver, real HTTP/2 wire

## Actual integration run — 27 October 2026

**PASS on the Mac using Node 26.0.0 and existing pinned local test dependencies.**

This wave executes Flind's **original Git-staged** `WorkerIngestServer`
and **original Git-staged** `GrpcStreamIngestDriver` together through
real loopback HTTP/2 gRPC, using the first-party generated Protobuf protocol.
Unlike Wave192's isolated class execution, the original server and production
driver are now connected in one actual gRPC exchange.

Command:

```bash
node tools/flind/qualify_production_grpc_driver_wire_wave193.mjs
```

The qualifier stages 13 first-party source files directly from Git HEAD
into fresh marker-owned scratch, compiles them offline with already-cached
esbuild/Connect/Protobuf, then runs an actual gRPC server/client exchange.
Only the **joined ingestion pipeline** and two small helper/logger interfaces
are replaced by explicitly scoped test doubles. They do not persist data.
The qualifier removes only its own scratch on exit; it never modifies the
cached upstream Node workspace or installs dependencies.

### Verified in the actual run

- Both original product classes ran together over loopback HTTP/2 gRPC.
- The client sent two synthetic messages using original generated Protobuf.
- The production driver deserialized them to buffers and forwarded the proper
  stream identity, sequence, offsets, topics, and unlimited budget.
- The synthetic pipeline kept a 115ms asynchronous side-effect barrier open.
- Original server returned the ACK **after** that barrier settled.
- The test pipeline timed out one of two messages. Actual gRPC response
  counted **1 accepted** and **1 unfinished/replayable offset 101**.
- Git-staged first-party file count = **13**. The test ran offline and
  returned exit code 0.

Actual machine-readable result fields:
`real_http2_proto_stream_pass=true`,
`original_grpc_driver_used=true`,
`original_grpc_server_used=true`,
`no_early_ack_before_side_effects=true`,
`timed_out_offset_replayable=true`.

### Scope limits: release NO-GO

**No real ClickHouse write occurred in Wave193.** The side-effect is a
delayed Promise, not a durable DB receipt. The actual
`createJoinedIngestionPipeline`, `GrpcIngestPipeline` dependencies,
production Rust consumer, Kafka commit/rebalance and multi-worker recovery,
authenticated tenant boundaries, SDK→API→Dashboard and product exactly-once
claims remain unqualified. Some helpers/logging are test doubles, although
the server, driver and proto paths are the originals.

Wave190–191's real Kafka/ClickHouse synthetic integration remains separate:
combining its verified disk writes with this actual production driver and
the real joined pipeline is the next missing end-to-end gate.

Issues #82/#5 remain open. Flind stays PRIVATE, actions disabled, no
deploy/release/publish, no paid compute or customer data.
