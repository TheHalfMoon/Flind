# Flind Wave 202 — drain accepted batches after gRPC stream disconnect

## Original production defect reproduced locally

In the original `nodejs/src/ingestion/api/grpc-server.ts`,
`WorkerIngestServer.totalInFlight()` only counted `inFlight` on
currently connected stream objects. But an accepted batch still belongs
to the shared ingestion pipeline after its caller disconnects. The
server intentionally tracks this via `acceptedBatches` until settled.

If a client disconnects while a batch is accepted and a pipeline
`next()` subsequently returns transient `null`, the pump loops back.
Before this fix `totalInFlight() === 0`, and the pump could park
indefinitely without collecting the accepted batch result. The
admission slot and shared in-flight metrics could stay occupied,
preventing new requests from making progress.

### Red test — actual original server and driver

```bash
node tools/flind/qualify_grpc_orphan_batch_recovery_wave202.mjs
```

The fixture stages 13 original product sources exactly from Git HEAD,
compiles them with preinstalled local Node26/Connect/Protobuf/esbuild
dependencies, and runs the original server and
`GrpcStreamIngestDriver` against an explicitly **synthetic** in-memory
pipeline. The fixture invokes the original server's streaming
generator API directly: a client response iterator is closed after an
actual batch has been accepted, the next pipeline pull returns
transient `null`, and the later completion must still be drained.

Before the fix, the original source failed:

```
AssertionError: server must count orphaned accepted batches,
not only live gRPC streams
actual: 0
expected: 1
```

The gRPC HTTP/2 server is created, but this particular focused
fixture closes the original streaming generator directly. **It does
not qualify actual HTTP/2 disconnect signaling from Connect clients.**

### Original production correction

`totalInFlight()` now counts every pending accepted batch from the
shared `acceptedBatches` map, *including orphaned batches whose
stream no longer exists*. It also counts unaccepted/admission-parked
batches still tracked in live streams without double-counting
accepted ones. No change to Kafka message content, protobuf,
admission slot size or consumer ACK semantics.

An additional native Jest regression is added to the original
`grpc-server.test.ts`. The complete native Jest workspace is
not installed in this environment and that authored test is not
claimed to have been run.

### Qualification scope and release decision

Focused source-backed original server/driver tests are not equivalent
to a full production ingestion test with real native Rust consumers,
Kafka rebalance, production joined analytics, ClickHouse persistence,
tenant identity, Django APIs and browser SDK/UI. These are outstanding
release gates.

Flind stays PRIVATE. Do not deploy, publish, enable Actions,
use paid services or customer data. Release remains NO-GO.
