# Flind Wave 190 — Actual Kafka → native Rust client → original Node gRPC server → supported durable ClickHouse

## Verification — 27 October 2026

**PASS: two independent, real, synthetic-data integration runs** of the same native Kafka→Rust→Node→ClickHouse test chain, the first ~**62.0 s** and the final exact proposed code ~**74.3 s** on a fresh isolated scratch and fresh Kafka broker. **10/10 focused fail-closed Python guards PASS** (`-W error::ResourceWarning`). Both integration runs ended with real Rust process exit 0, original Node gRPC server exit 0, exactly **one** accepted synthetic batch after verified ClickHouse disk readback, and **native Rust Kafka consumer group committed offset 3**, followed by bounded shutdown and marker-checked removal of the owned Kafka broker scratch.

This is the first time in this qualification sequence that all four services appeared in **one live test path**. It is **not** a production Flind end-to-end pass: the Rust executable is a **new minimal test client using real `rdkafka` 0.37.0 and Flind's unmodified first-party generated Rust `ingestion-worker-proto`**, not the original production `ingestion-consumer` binary or its scheduling/rebalance/batcher logic. The Node server is the original first-party `WorkerIngestServer` over real HTTP/2 gRPC, but the backing `StreamIngestDriver` and logger are **clearly test-only shims**, not the production `BatchingPipeline`, DB engine or ingestion stores.

### Actual source-backed flow

1. Wave179's marker-owned private **Kafka 4.3.1 KRaft** process receives exactly three synthetic JSON events, two from team 101 and one from 202. Its original helper publishes with broker ACK and independently checks records in another test consumer group.
2. `tools/flind/wave190-rust-kafka-node/src/main.rs` runs an actual **native Rust `rdkafka::BaseConsumer`**, with automatic offset commits and automatic offset storing disabled, checks all three exact Kafka payloads and consecutive offsets **0–2**, and constructs the original Flind `KafkaMessage` Protobuf frames.
3. That Rust client connects using `tonic` over real **HTTP/2 gRPC** to the **original, Git SHA-attested Node `WorkerIngestServer`**, sends the original typed hello and one sub-batch, and awaits the actual `SubBatchAck(seq=1, status=OK, accepted=3, unfinished=[])`.
4. The bounded **test-only Node driver** accepts only the three exact synthetic records. It creates a real **MergeTree** table in official supported ClickHouse **25.12.7.21**, inserts the three fixture rows, then launches a **second independent ClickHouse OS process** to reopen that same on-disk table and validate exact UUID/event/team data. **Only after this disk readback succeeds does the test driver settle the batch**, permitting Node's original gRPC server to send its ACK.
5. **Only after the ACK** does the Rust `rdkafka` consumer call **`commit(..., CommitMode::Sync)`** for offset **3**, and verify the broker's returned committed offset is precisely **3**. Node then stops, reports `durable_three_reopened=true` and `accepted_batches=1`, and exits zero; the owned Kafka process is stopped and its private temporary log directory is removed.

The temporary Node listener is an ephemeral port and the Rust client targets `127.0.0.1`. The original Node server's bind behavior has **not** been independently proven to be network-restricted; none of these processes is a deployment. Only entirely synthetic events were handled.

### Provenance and build

- **Original first-party Rust Protobuf source attested** using exact local offline Git blobs from Flind source commit `1905e9afb0f25f2685f042485b59f4c433403ffe`: `rust/ingestion-worker-proto/src/lib.rs`, `build.rs`, and `proto/ingestion/worker/v1/worker.proto`. No new wire schema was invented.
- **Eight original first-party Node server/budget/metrics/type/Protobuf modules** were separately Git-blob SHA-attested. The `grpc-server.ts` blob was `5a32b131056bb1e7f10e8bca824c149097d2d563` and generated `worker_pb.ts` was `c9d57314ca63412ff5c15d2c6d3b8e900ce774a7`. The original Connect HTTP/2 session-manager patch and five exact Wave186 dependency versions remained applied and verified in the isolated Node scratch.
- The new, minimal native Rust test client is stored under `tools/flind/wave190-rust-kafka-node/`, with its **exact `Cargo.lock`**. The repo manifest's relative path points to the original `rust/ingestion-worker-proto` crate. Local disposable build used an equivalent absolute path to the **Git-verified** original checkout; the qualifier refuses any mismatch with the tracked manifest, source, or lock. All three staged artifact files were independently checked against their exact proposed GitHub blob hashes.
- First Rust `rdkafka-sys` build attempt **failed to locate macOS C++ headers** (`string` and `iostream`). Rebuilding with the system SDK root `SDKROOT` and `CPLUS_INCLUDE_PATH=$SDKROOT/usr/include/c++/v1`, `cargo build --offline -j 2` completed **successfully in ~104.5 seconds**. No paid compute.
- Official supported ClickHouse compressed macOS arm64 release `v25.12.7.21-stable` was SHA256 checked using the Wave189 source-attested verifier: `e5be46727e773893b5786aaa3d28f5661a30179fe65e19096d8eb7d41a554fd6`. The original, immutable compressed download remains separate from its self-unpacking runtime executable, which is used only in the marked scratch. Only the six verified first-party `events_recent` column types are used in a **fixture-specific table**, not the full production schema.

### Tests and fail-closed qualifications

`tools/flind/qualify_native_rust_kafka_node_mergetree_wave190.py` is a bounded, scratch-scoped reproduction tool. It checks test ownership, pinned original Rust proto, exact tracked Rust test client/manifest/`Cargo.lock`, eight original Node Git blobs, approved original Connect patch/packages, source-supported ClickHouse version and official binary digest. The tool **never downloads packages or publishes/deploys** on its own. The Kafka broker and ClickHouse process are started in explicitly owned temporary folders. Run with a **new** marker-compatible path under `/private/tmp`:

```bash
python tools/flind/qualify_native_rust_kafka_node_mergetree_wave190.py \
  --scratch /private/tmp/flind-wave190-my-fresh-run
```

The connected Mac runtime for this qualification had already prepared an offline pinned Rust test binary, the original source checkout and the approved Node dependency scratch; this command does **not** automatically bootstrap them, and those hard-coded working paths must exist. It refuses an existing scratch directory, non-`/private/tmp` scope, changed original source blobs, modified Rust fixtures or changed Node packages/patches.

The final run reported `actual_native_kafka_proto_node_durable_test_bridge_pass=true`, `native_rust_commit_verified=true`, `native_rust_committed_offset=3` in the Rust fixture, `owned_node_stopped=true`, `owned_kafka_stopped=true`, `owned_kafka_scratch_removed=true` and `release_qualified=false`. The separate focused guard file `tools/flind/test_native_rust_kafka_node_mergetree_wave190.py` passed **10/10**, including refusals of malformed/forged ACKs, fractional/bool/string/wrong committed offsets, two accepted batches, missing disk readback, false shutdown, unexpected preexisting scratch, altered original proto bytes and forged product-ready flags. The focused tests supplement rather than replace the **two successful real integration runs**.

### What Wave 190 still does **not** prove

- Original **production Rust `ingestion-consumer`** polling, rebalance, worker registration, production batcher and checkpoint scheduling running live with the **production Node `StreamIngestDriver`**.
- The original Node production batching/processing pipeline, complete HCL ClickHouse table migration/materialized Kafka views, durable PostgreSQL metadata, production data ingestion and tenant-authenticated query APIs.
- Kafka broker crash/restart, exact-once/idempotent event persistence under repeated ACK loss, retry/replay across deployments or a durable broker offset state after the **intentionally deleted test broker**.
- Full SDK→authenticated API→Dashboard/browser or desktop E2E, complete PostgreSQL migrations/rollback and OAuth/PKCE/JWKS, final installer release artifacts and Flind-only identity/asset endpoint audit.

**Keep release issue #82 and identity issue #5 OPEN / Release NO-GO.** Repo stays PRIVATE; inherited GitHub Actions disabled. Do not publish/deploy, use paid services, ingest customer data, or remove mandatory third-party license/copyright notices.
