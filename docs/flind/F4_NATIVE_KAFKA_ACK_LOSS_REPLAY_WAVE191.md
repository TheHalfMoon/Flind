# Flind Wave 191 — native Kafka consumer: hard crash AFTER durable ClickHouse, BEFORE gRPC ACK

## 27 October 2026: real crash/recovery tests PASS twice

Wave191 verifies a **specific failure window** of the previous Wave190 four-component integration. The real source-attested sequence uses a newly compiled synthetic Rust `rdkafka` client with Flind's **original** generated `ingestion-worker-proto`, the **original** Node `WorkerIngestServer` over actual HTTP/2 gRPC, a real isolated Kafka 4.3.1 KRaft broker, and the **official supported ClickHouse 25.12.7.21 MergeTree** backed by disk. The Node `StreamIngestDriver` is deliberately a **test double**; this is not the product's deployed ingestion pipeline.

The important distinction from Wave190 is that Wave191 deliberately destroys the Node server after the durable disk confirmation **but before the original gRPC server can send an ACK**. It then checks the Kafka consumer group's committed offset, restarts the original Node gRPC server with a test-only recovery driver, and replays the identical events.

### Actual steps and results

1. Start an independently owned private **Kafka4.3.1** broker, with three synthetic events; the existing Wave179 producer/consumer test confirms Kafka delivery independently.
2. Verify eight original first-party Node Git blobs and three original Rust Protobuf source files against the pinned private Flind source commit `1905e9afb0f25f2685f042485b59f4c433403ffe`. Validate the unchanged original Wave190 Node test fixture via **Git SHA-1 blob `5d688ed7e7df4a21dabe15982b926373ae1502bf`**, and verify the pinned Connect/Protobuf packages and original Connect HTTP/2 patch. Stage all modifications **only** inside a marker-owned disposable Node test scratch, not the original repo.
3. The original Node gRPC server receives the three native Rust Kafka messages. Its synthetic driver writes all three to a real **MergeTree**, closes the ClickHouse process, launches another independent ClickHouse process and verifies the three synthetic UUID, event, properties, `distinct_id`, and team values.
4. Immediately **after** this successful disk readback, the test-only driver performs a deliberate `process.exit(73)` **before creating/completing the gRPC ACK**. The real native Rust client fails the request. Its test consumer-group committed Kafka offset remains **unset/negative**. A separate ClickHouse process can still recover all **3/3 persisted UUID/event/team rows** and the MergeTree on-disk part checksums.
5. The same Kafka broker remains running. On recovery, launch the same original Node gRPC server and same native Rust client against the existing on-disk MergeTree. A clearly labeled **test-only recovery driver** does **not** reinsert previously persisted fixture rows; instead, it verifies all three existing rows and permits the original server to ACK.
6. The actual native Rust client receives the successful original gRPC ACK, makes a **synchronous Kafka committed offset=3**, and checks the reported committed offset. A final independent ClickHouse process verifies **3/3 original events**, with no duplicate rows. The Node server shuts down cleanly; the owned Kafka broker stops and its marker-owned scratch is deleted.
7. The verifier restores **both** the original Wave190 Node fixture source **and its generated JS bundle** after success/failure; the final receipt explicitly reports `original_node_test_bundle_restored=true`.

The two actual **independent integration runs PASS**:
- First real end-to-end fault-injected run ~**74.9 seconds**.
- Second real run using the **exact final hardened code** on a **new isolated Kafka/ClickHouse scratch** ~**69.8 seconds**, process exit 0.

The second final receipt is checked into `docs/flind/evidence/F4_WAVE191_NATIVE_KAFKA_ACK_LOSS_REPLAY_FINAL_RECEIPT.json`. Key result flags:
- `real_ack_lost_replay_integration_pass=true`
- `child.node_crash_after_disk_before_ack_exit=73`
- `child.offset_uncommitted_after_node_crash=true`
- `child.original_rust_replayed_and_committed_offset=3`
- `child.recovery_node_grpc_ack_received=true`
- `child.synthetic_persisted_event_count=3`
- `child.test_only_recovery_no_reinsert=true`
- `owned_kafka_stopped=true` and `owned_kafka_scratch_removed=true`
- `original_node_test_bundle_restored=true`
- `production_rust_ingestion_consumer_qualified=false`, `production_node_ingestion_driver_qualified=false`, `exactly_once_product_qualified=false`, `authenticated_tenant_isolation_qualified=false`, `release_qualified=false`

### Fail-closed tests: 11/11 PASS

`tools/flind/test_native_kafka_ack_loss_replay_wave191.py` passed **11/11 tests** using warnings-as-errors. It explicitly rejects a changed upstream Node source hash, premature ACK, a forged native Rust recovery-success receipt, a missing valid Node stop receipt, a committed offset after intentional crash, incorrect persisted UUID/team/event rows, unexpected Node exit code, and reuse/overwrite of an unowned scratch. During test-driven repair, the ninth test found a false-positive admission possibility: with mocked downstream results, the verifier could report replay success despite a missing native Rust ACK receipt. The finalized code now **requires both the actual native Rust ACK/commit receipt and the successful original Node durable-shutdown receipt**. All 11 guards pass on that final code; the final real integration also passed after the repair.

### Reproduce locally

The harness `tools/flind/qualify_native_kafka_ack_loss_replay_wave191.py` accepts a new, empty direct child of `/private/tmp`, prefixed `flind-wave191-`, and relies on the scoped, already-installed Wave190 test requirements: verified first-party Git source checkout, locally compiled native Rust rdkafka test binary, exact pinned original Node Connect dependency scratch and original Connect patch, cached Kafka4.3.1, and the SHA-256-verified official ClickHouse25.12.7.21 compressed asset. **The harness itself never installs packages, opens external services or deploys.**

```bash
python tools/flind/qualify_native_kafka_ack_loss_replay_wave191.py \
  --scratch /private/tmp/flind-wave191-new-isolated-run --json
python -W error::ResourceWarning -m unittest \
  tools.flind.test_native_kafka_ack_loss_replay_wave191 -q
```

The tool refuses stale or preexisting folders, uses fixed private-loopback test traffic, launches at most one owned Kafka broker, uses bounded ClickHouse subprocess memory/time and deliberately avoids reading customer data. The first full attempt to run Wave191 did not start services because it reused Wave190's stricter `flind-wave190-` scratch-prefix initializer for a `flind-wave191-` directory. This fail-closed setup issue was corrected by maintaining the inherited owner markers while creating **a separately scoped Wave191 scratch**. It was never a product bug or a passed test.

### Why release remains blocked

The native Rust binary is a **new test client using real rdkafka**, not the original production `ingestion-consumer` process with live rebalance, worker registry and batch/checkpoint scheduler. The Node gRPC server is the original product code, but **its ingestion driver and replay/no-reinsert decision are synthetic test doubles**, not the production `BatchingPipeline`, deduplication algorithm, or actual durable ClickHouse ingestion views. This test validates ACK/offset ordering and synthetic replay under one precisely chosen fault window; it does **not** prove production exactly-once, multi-process power-loss recovery, concurrent workers, tenant authorization, or a live version of all backend and frontend services.

Remaining major blockers: original production Rust ingester → original production Node `StreamIngestDriver` → complete ClickHouse ingestion/materialized views; Kafka broker crash/restart and idempotence under multiple replays; authenticated tenant-scoped Django API and SDK→Dashboard/browser E2E; PostgreSQL migration apply/rollback; OAuth/PKCE/JWKS and Flind-only branding, assets and distribution verification.

**Issue #82 and #5 remain OPEN — Release NO-GO.** Repository stays PRIVATE with inherited GitHub Actions disabled. No publication/deployment, paid models/compute, actual user records or removal of legally required third-party copyright/license notices.
