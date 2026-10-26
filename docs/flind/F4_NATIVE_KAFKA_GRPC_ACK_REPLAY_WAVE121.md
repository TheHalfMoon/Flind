# Wave 121 — Original Rust Kafka/gRPC processing, ACK frontier, partial ACK, and replay E2E

## Why this is a material step forward

Previous Waves 117–120 qualified compilation, native Rust Kafka group membership, and the runtime health gate. Wave121 runs **actual production ingestion-consumer Rust logic, actual Kafka4.3.1 broker, first-party genuine WorkerIngest gRPC test server, and actual Kafka offset-commit verification**. It does **not** replace the Node production ingestion worker or ClickHouse schema; the worker remains an explicitly **test-owned first-party** implementation using the real protocol.

Rather than inventing a simplified event loop, `tools/flind/qualify_original_rust_grpc_kafka_wave121.py` runs three **already present original upstream Rust E2E tests** from the tracked `rust/ingestion-consumer/tests/e2e_integration_test.rs`:

1. `the_committed_offset_is_the_ledger_frontier`: checks Kafka's real committed offsets advance only to the acknowledged processing ledger frontier.
2. `a_partial_ack_redelivers_only_the_unfinished_messages`: checks a real gRPC partial-ACK failure causes replay of only unfinished messages and preserves per-key ordering.
3. `consumer_crash_before_commit_redelivers_without_loss`: checks crash/restart before Kafka commit replays uncommitted events without losing work.

## Execution and verifiable evidence — October 26, 2026

The harness creates **one disposable actual Apache Kafka 4.3.1 KRaft broker** bound to loopback. Before any test, it:
- Confirms the original upstream Rust test file's **Git tree object** exactly matches Flind `main`, and the temporary test checkout is clean.
- Temporarily overlays the **current Flind main** Rust `consumer.rs`, `rebalance.rs`, `worker_registry.rs` and `main.rs` into the older preexisting fuller checkout. Those files are restored byte-for-byte in `finally`.
- Replaces **only** the original E2E test's `KAFKA_BROKERS = localhost:9092` constant with the actual private ephemeral broker's `127.0.0.1:<port>`, again restoring the file byte-for-byte afterward. It does not use or alter production Kafka brokers.
- Runs `cargo test --locked --offline -p ingestion-consumer --test e2e_integration_test <exact approved test name> --jobs 2 -- --exact --nocapture`, one test at a time, with a strict three-name allowlist, <=130-second total run cap, at least 10GiB disk reserve, native local Apple SDK, and no paid or online dependencies.
- Independently checks the original Rust test process **exit 0** and the literal `test <name> ... ok` and `test result: ok. 1 passed;` output, refusing unexecuted/filtered tests.

**First ran all three separately with actual Kafka: 3/3 PASS.** Then repeated all three *sequentially against one private actual Kafka broker*: **3/3 PASS, exit 0**. Combined Rust test execution ~32.1s; broker fixture end-to-end ~48.5s. All temporary Rust overlays restored, broker stopped and temporary storage cleaned. Free Mac disk remained around 12GiB.

```sh
python3 -m tools.flind.qualify_original_rust_grpc_kafka_wave121
python3 -m unittest -v tools.flind.test_original_rust_grpc_kafka_wave121
```

The second command's **7 focused admission tests PASS**, covering exact allowlisted original tests, rejecting non-loopback Kafka, unsupported/duplicate test selections, missing original full checkout, accurate release flags, original Git source provenance, offline and bounded Cargo arguments.

## Accurate qualification scope

**Qualified:** real first-party Rust ingestion-consumer runtime against real Kafka and a **first-party Rust test gRPC worker**, with tests that assert ACK frontier, selective redelivery after partial ACK, and crash/restart no-loss behavior using actual Kafka commits and readbacks.

**NOT qualified:** deployment of real `nodejs/src/ingestion` worker or Rust Kafka-consumer-to-Node gRPC implementation, persistent **production** ClickHouse `events` table and ingestion transforms, authenticated tenant query API, Dashboard/browser, OAuth, full frontend/desktop builds, whole-service deployment, and release. This uses a real protocol but a **fake business processing worker**, so it is not a customer-data end-to-end test.

Repo remains private, inherited GitHub Actions disabled, no publication/deployment, no paid cloud services, and mandatory third-party attributions preserved. Keep Issue #82 OPEN and product release NO-GO.
