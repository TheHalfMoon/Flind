# Wave 123 — Real Rust/Kafka/gRPC worker failover and in-order replay E2E

## Execution objective

Wave121 qualified real broker Kafka offset-frontier, partial ACK and crash replay correctness. Wave122 qualified lost ACK, 4xx poison refusal and partial acceptance failures. Wave123 qualifies genuine **worker-fleet failover** through three additional **original first-party** `rust/ingestion-consumer/tests/e2e_integration_test.rs` cases against an actual isolated Apache Kafka 4.3.1 KRaft broker, **actual production Rust ingestion-consumer**, and original protocol-compatible **first-party Rust test** WorkerIngest gRPC workers:

1. `failing_worker_triggers_rerouting`: one worker's HTTP readiness fails, and new events for its key route to the healthy worker in original sequence.
2. `drainer_crash_mid_drain_replays_to_survivor_in_order`: a worker crashes while an in-flight request is held and subsequent batch deferred; accepted work is not lost and must reach the surviving worker in original per-key order.
3. `nacking_worker_fences_worker_stream_and_reroutes_in_order`: a worker stops receiving work and NACKs; the stream is fenced and new messages reroute to a surviving worker with preserved per-key order.

No production Node worker, customer data, paid service, external Kafka broker or product ClickHouse table is involved.

## Reproducibility and results (October 26, 2026)

`tools/flind/qualify_original_rust_grpc_kafka_wave121.py` adds only the above **three exact original Rust test names** to its allowlist (`RECOVERY_CASES`); its previous Wave121 three-test default and Wave122 failure cases are preserved.

`tools/flind/qualify_rust_grpc_worker_failover_wave123.py` requests exactly these tests from the existing verified offline native Rust/Kafka harness. It uses one temporary Kafka 4.3.1 broker, checks the exact original tracked E2E source Git tree matches Flind `main`, patches the original hardcoded localhost:9092 E2E test host constant to the actual isolated Kafka broker only within an older temporary full checkout, temporarily overlays the latest tracked Flind consumer sources, enforces a 10 GiB disk floor and a <=130-second bounded test suite, and restores all original temporary source files byte-for-byte when done. It independently inspects native `cargo test --exact` one-case output and exit code.

```sh
python3 -m tools.flind.qualify_rust_grpc_worker_failover_wave123
python3 -m unittest -v \
  tools.flind.test_rust_grpc_worker_failover_wave123 \
  tools.flind.test_rust_ingestion_failures_wave122 \
  tools.flind.test_original_rust_grpc_kafka_wave121
```

**Actual Rust Kafka/gRPC E2E: 3/3 PASS, exit 0**, in one private broker session. The native integration receipts show real Kafka4.3.1 broker true, all three exact first-party cases true, temporary source checkout restored true, and product/release gates all false.

Focused Python tests also PASS. The repo's temporary full checkout remained clean; the Mac preserved around **12GiB free** and no cloud resources were used.

## Qualification boundary

Nine original first-party Rust/Kafka/gRPC E2E cases have now passed across Waves 121–123, covering success, ACK failure, crash/restart and worker-fleet failover. They use an actual Kafka broker, actual Rust Kafka consumer logic and actual **gRPC protocol with synthetic Rust test worker**. These runs are **not** proof of a booted and functioning production Node `nodejs/src/ingestion` worker; nor do they prove product ClickHouse durable `events` storage, transformations/persons, tenant-scoped query API, Dashboard/browser, OAuth or full release.

Release remains NO-GO; keep Issue #82 open. Repository private and inherited GitHub Actions disabled; no deployment/publication, paid cloud or removal of third-party donor legal notices.
