# Flind Wave 187 — Real typed Rust Protobuf client → original Node WorkerIngestServer over gRPC

## Verification — 27 October 2026

**PASS:** a newly compiled, standalone **Rust client using the real first-party Flind \`ingestion-worker-proto\` crate**, sent Flind's generated \`StreamHello\` and \`SubBatch\` messages through a live **HTTP/2 gRPC connection** to the **original Git-verified Node \`WorkerIngestServer\`** qualified in Wave186. The Node server immediately sent its ready frame; the Rust client obtained **one exact successful batch ACK (\`seq=1\`, accepted=1, \`SubBatchStatus::Ok\`)**. The same Rust client then tested invalid \`seq=2\` on a fresh stream and verified that the server rejected it **without an ACK**. After Rust exited 0, the owned Node test server stopped with exit 0 and reported **exactly one** synthetic accepted batch.

This is a real cross-language protobuf + tonic + Connect **network integration**. **It is not the production Rust Kafka ingestion-consumer**: the Rust client is a new minimal synthetic protocol fixture built against the original proto crate, not the production consumer polling Kafka. The Node server is real, but its logger and processing driver are **explicit test doubles**, not the actual batching pipeline or durable ClickHouse sink.

### Grounded first-party sources

The original Rust modules were verified byte-for-byte against the pinned, private Flind Git source commit \`1905e9afb0f25f2685f042485b59f4c433403ffe\`:

- \`rust/ingestion-worker-proto/src/lib.rs\`, blob \`ced9e9ee4254c52fa2e0db14a7f546078b2d61ef\`
- \`rust/ingestion-worker-proto/build.rs\`, blob \`448a0df9c6e8de772434e2790e6c5947bdb9ccae\`
- \`proto/ingestion/worker/v1/worker.proto\`, blob \`0caed14e3a622a75ff1dc4f47b714b9db0e6cf71\`

Eight exact original Node source blobs—server, generated TypeScript Protobuf, converters, metrics, budget, stream sentinel and types—were separately reverified by the Wave186 source attestation, including \`grpc-server.ts\` blob \`5a32b131056bb1e7f10e8bca824c149097d2d563\` and generated \`worker_pb.ts\` blob \`c9d57314ca63412ff5c15d2c6d3b8e900ce774a7\`.

### Tests and implementation

- New tracked minimal Rust client: \`tools/flind/wave187-rust-client/Cargo.toml\`, \`src/main.rs\`, and exact \`Cargo.lock\`. Its \`ingestion-worker-proto\` dependency is the **existing original Flind crate**, not a copied/simplified/rewritten protobuf schema. The Rust fixture uses tonic 0.12.3 (same major/minor version as Flind's current Rust workspace), tokio and tokio-stream. All dependencies are free/open-source. No paid inference/services.
- Original Node server fixture: \`tools/flind/verify_rust_proto_node_server_wave187.mjs\` and \`build_rust_proto_node_server_wave187.mjs\`. Uses the exact Git-attested Node modules staged by Wave186 with original pinned Connect 2.1.1, Protobuf 2.11.0, prom-client 14.2.0, esbuild 0.25.12 and Flind's existing patched HTTP/2 session manager. The small driver accepts **only** the exact synthetic topic \`flind_wave187_rust_proto\`, partition0, offset187, and specified synthetic UUID; it acknowledges accepted work without real database writes. Original Node logger is replaced **only in this test scratch** by a no-op shim.
- The first Cargo \`--offline\` run refused to build because \`adler2\` was not in the local cache. A follow-up bounded **free crates.io** build populated the missing dependency cache and **successfully compiled** the Rust client in approximately **33.35 seconds**, using two jobs. It has subsequently been stored with a \`Cargo.lock\` to make exact dependency selection reproducible.
- The direct actual Rust→Node test returned \`original_rust_proto_client_wire_pass=true\`, \`real_node_http2_ack_verified=true\`, \`bad_rust_seq_refused=true\`, Rust exit0 and Node stop exit0 with \`accepted_synthetic_batches=1\`. There was **no** real Kafka consumer or ClickHouse involved.
- \`tools/flind/qualify_rust_proto_node_grpc_wire_wave187.py\` verifies the 3 original Rust proto source blobs, 8 Node source blobs, exact Rust fixture source and manifest, marked scratch ownership, five approved Node package versions and first-party Connect patch, then runs the original Node server with the actual compiled Rust client, checks exact success and rejected frames, and terminates the owned Node process in a \`finally\` barrier. The exact independently reproducible full qualifier **PASS** in approximately **27.5 seconds**; \`original_rust_proto_to_real_node_grpc_qualified=true\`, \`node_server_stopped=true\`, \`rust_node_ack_count=1\`, \`release_qualified=false\`.
- **8/8 Python qualification/guard tests PASS**, \`-W error::ResourceWarning\`, including a **separate second actual Rust→Node wire run**, fake ACK/ready rejection, extra or fake ACK counts, forged product/release flags, missing scratch ownership, source drift and all production gates false.

### Reproduction and scoped safety

The full qualifier requires a marker-owned Node Wave186 dependency scratch and a separate marked Rust client scratch, with the Rust crate built from the pinned tracked \`Cargo.lock\`, **without changing the original repo or old full checkout**. The Rust scratch marker \`.flind-wave187-rust-owner\` contains \`FLIND_WAVE187_RUST_CLIENT_V1\` with a trailing newline. In the repo, the Cargo manifest points to \`../../../rust/ingestion-worker-proto\`; in the isolated Mac scratch used for the proof that path was explicitly remapped to the verified local first-party source checkout. Build from the repo directly when its Rust original source is locally present.

The qualifier itself **does not download or install packages**, nor deploy any service. The temporary original Node server binds an ephemeral port with the original \`WorkerIngestServer.start()\` behavior and the client calls **127.0.0.1**; a short-lived test process with a 45-second watchdog is used, but the original server's bind behavior **does not prove network/firewall confinement or release-grade security**.

### Product blockers not cleared

The next actual gate is **production Rust Kafka ingestion-consumer → original Node WorkerIngestServer using the production ingestion driver → persistent ClickHouse engine with replay/offset correctness**, then tenant-authenticated Django queries/SDK/browser Dashboard and full PostgreSQL migrations/rollback, OAuth and final Flind product identity audit.

The Wave184 original Rust Kafka/test-gRPC nine-case reliability proof and Wave186 Node server wire proof are **independent** of this Wave187 typed cross-language smoke; none alone or combined qualifies the complete production processing path.

**Release issue #82 and Flind identity issue #5 stay OPEN; release NO-GO.** Repository remains PRIVATE, inherited Actions disabled; no publication/deployment, paid models/compute, production customer data or removal of legally required third-party copyright/license notices.
