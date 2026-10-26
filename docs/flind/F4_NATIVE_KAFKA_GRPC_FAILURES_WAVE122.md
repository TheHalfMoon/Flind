# Wave 122 — Original Rust Kafka/gRPC negative ACK and poison-batch failure E2E

## Extending actual native evidence beyond happy-path ACKs

Wave121 qualified three already existing first-party Rust ingestion-consumer E2E tests for commit-frontier correctness, selective partial-ACK replay and crash/restart recovery against **actual private Apache Kafka 4.3.1**, using the first-party Rust test WorkerIngest gRPC server.

Wave122 adds a separate **three-test original Rust E2E failure-mode set**, using the *same actual production Rust consumer code, original first-party E2E tests, real broker and actual gRPC protocol*:

- `lost_ack_after_processing_replays_without_loss`: the test worker processes a batch but **drops a gRPC ACK**; the Rust consumer retries and preserves all distinct event sequences in Kafka order. Duplicates may occur after lost acknowledgement; the test explicitly expects replays, **not exactly-once downstream processing**.
- `poison_batch_fails_safely_without_committing`: both original gRPC test workers return a 4xx rejection; the native consumer fails rather than counting rejected records as successfully ingested.
- `partial_acceptance_fails_the_batch_without_commit`: worker returns an incomplete acceptance of a batch; the native consumer fails safely rather than committing an unaccepted frontier.

These are genuine original test functions in the unchanged first-party `rust/ingestion-consumer/tests/e2e_integration_test.rs` file, with the exact upstream Git tree checksum verified. They are not mocked functions.

## Reproduction and actual result — October 26, 2026

`tools/flind/qualify_original_rust_grpc_kafka_wave121.py` now exposes a strict allowlist of these three additional original test names while preserving the original Wave121 three-test default. It still rejects arbitrary/unapproved names, non-loopback brokers, dirty temporary test checkouts, missing proto, and less than 10GiB disk. No production source/config, Kafka offsets, donor licenses or Git history is rewritten; the local temporary complete Rust checkout test-host constant and current product source overlay are restored byte-for-byte after each session.

```sh
python3 -m tools.flind.qualify_rust_ingestion_failures_wave122
python3 -m unittest -v \
  tools.flind.test_rust_ingestion_failures_wave122 \
  tools.flind.test_original_rust_grpc_kafka_wave121
```

The **actual first-party Rust E2E cases passed 3/3 (exit 0)** against a private Kafka 4.3.1 broker in one bounded session. All temporary source overlays restored and broker shut down. `test_rust_ingestion_failures_wave122.py` adds fixture-refusal and release-guard checks; the combined original Wave121+Wave122 Python unit suite also passed.

## Scope and important nuance

**Qualified:** first-party Rust Kafka/gRPC test-worker failure and replay logic in six in-tree tests across Waves 121–122, including broker committed-offset frontier, selective partial ACK replay, crash before commit recovery, dropped gRPC ACK replay, 4xx poison refusal, and incomplete acceptance refusal.

**Not qualified:** production Node.js gRPC worker (these tests use Rust test worker), actual app event processing/transforms/persons, durable production ClickHouse `events` storage, authenticated tenant query API, Dashboard/browser, OAuth/PKCE or complete release. In particular **a lost ACK can lead to duplicate delivery**; the observed original test proves no loss and replay, not magical exactly-once delivery.

Keep #82 OPEN, product release NO-GO, private repo, inherited GitHub Actions disabled, no deployment or paid cloud, preserve legal donor attribution.
