# Flind Wave 184 — Nine original Rust Kafka/gRPC integration cases (real private Kafka)

## Result: 9/9 original first-party integration tests PASS (27 October 2026)

Wave184 qualifies **nine real, originally in-tree Rust `ingestion-consumer` integration tests** running against a newly created private Apache Kafka **4.3.1** KRaft broker and the suite's own **test gRPC WorkerIngest server**. This is not a simulated Rust consumer and does not use Python to emulate the Rust offset/frontier logic. It also **does not** run the Node production ingestion worker or persistent ClickHouse materialized Kafka pipeline.

### Source and environment provenance

- Test source `rust/ingestion-consumer/tests/e2e_integration_test.rs` and the four original Rust source files (`consumer.rs`, `rebalance.rs`, `worker_registry.rs`, `main.rs`) were taken from the exact offline SHA-1-verified tracked Git blobs of the private Flind source commit `1905e9afb0f25f2685f042485b59f4c433403ffe`.
- Their current GitHub `main` blob hashes were compared and **matched** that pinned source at verification time. This supports source consistency for these **five files only**, not a complete current-main rebuild/qualification or all dependency files.
- The existing disposable full source checkout at `/private/tmp/flind-wave76-frontend` had an older product-source baseline. Wave184 backed up its original bytes, verified clean approved paths, overlaid **only the exact five pinned source files**, changed only the test fixture's one `localhost:9092` broker address to the newly reserved `127.0.0.1:<ephemeral-port>`, then used a `finally` barrier to **restore every original file byte for byte** after each case. No production source change is proposed.
- Used the existing locally cached official **Kafka4.3.1**, previous `/private/tmp/flind-wave110-rust-target` Cargo build cache and existing ClickHouse **25.12.7.21**, which is within Flind's source-declared supported version range. Kafka broker/controller bind loopback only, and logs/data live exclusively in marker-owned scratch.
- `cargo test --locked --offline -p ingestion-consumer --test e2e_integration_test <one allowlisted case> --jobs 2 -- --exact --nocapture`. Cargo network access disabled. Source blob lazy fetch disabled. Two Rust build jobs, `CARGO_INCREMENTAL=0`, stripped debuginfo profile, one run at a time.
- Strict **3GiB free-disk reserve** and **135-second wall deadline per individual Rust case**, plus the Wave179 broker memory/disk ceilings (JVM heap <=384MiB, scratch <=500MiB and separate minimum disk reserve). Kill **only** this tool's owned Cargo process group on resource/deadline breach. After every case, verify approved source-file restoration; stop the owned Kafka service group and verify marker-owned Kafka temp directory removal.

### Original integration cases actually executed

| Case | Result |
| --- | --- |
| `the_committed_offset_is_the_ledger_frontier` | **PASS** — offset / ledger frontier |
| `a_partial_ack_redelivers_only_the_unfinished_messages` | **PASS** — unfinished messages replay |
| `consumer_crash_before_commit_redelivers_without_loss` | **PASS** — crash-before-commit recovery |
| `lost_ack_after_processing_replays_without_loss` | **PASS** — lost acknowledgment replay |
| `poison_batch_fails_safely_without_committing` | **PASS** — poison batch refuses commit |
| `partial_acceptance_fails_the_batch_without_commit` | **PASS** — partial acceptance refuses commit |
| `failing_worker_triggers_rerouting` | **PASS** — failing worker reroute |
| `drainer_crash_mid_drain_replays_to_survivor_in_order` | **PASS** — draining-worker crash ordering |
| `nacking_worker_fences_worker_stream_and_reroutes_in_order` | **PASS** — NACKed worker fenced and rerouted |

All nine cases were run **individually against a live isolated Kafka broker** and finished with **`test result: ok. 1 passed; 0 failed`**, Cargo exit `0`, `full_checkout_source_restored=true`, `original_git_blob_source_verified=true`, `owned_kafka_process_stopped=true`, `owned_kafka_scratch_removed=true`. The fixed-name test gRPC server is part of the original Rust test executable — no production Node worker endpoint was exercised.

First and second attempts to build the original test executable exhausted their **135-second compile deadline**, safely terminated child builds, restored source and left the compiled Cargo dependency cache reusable. The third attempt completed compilation and passed the ledger case in roughly **29.4 seconds** of callback time; the other eight original cases each ran with cached Cargo dependencies. **Failed initial compile deadlines are preserved in the evidence rather than falsely counted as passes**.

The added `tools/flind/qualify_bounded_rust_grpc_e2e_wave184.py` is intentionally a **single-case** reusable qualification command. It **rejects** any scenario name outside the exact nine-case allowlist and never sets the production-worker/tenant/release flags. `tools/flind/test_bounded_rust_grpc_e2e_wave184.py`: **9/9 Python guard/unit tests PASS**, `-W error::ResourceWarning`, including offline Git content attestation, invalid topic destination, mismatched source checkout, unapproved case names, missing source blob, true/false receipt preservation and immutable release-blocker flags.

### What remains open

This closes the **nine-case original native Kafka→test-gRPC reliability smoke** for the pinned verified Rust files. **Not qualified:** real production **Node WorkerIngestServer / shared batch pipeline** with native Rust consumer, durable ClickHouse Kafka engine/Materialized View and MergeTree, exactly-once/idempotent recovery, authenticated tenant query APIs, original SDK→Dashboard E2E, complete PostgreSQL migrations/rollback, current-main full native executable/source build, OAuth/PKCE/JWKS, and end-user Flind-only identity/asset/installers/legal audit.

**Keep #82 and #5 OPEN / release NO-GO.** Repository remains PRIVATE, inherited GitHub Actions disabled, no publishing/deployment/paid models/compute/customer data; mandatory third-party attribution preserved.
