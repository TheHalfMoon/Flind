# Wave 120 — Native Rust ingestion readiness requires live Kafka assignment AND verified worker

## Observed production defect

Wave118 corrected a false readiness 200 when the native Rust consumer had no available Node worker. However its readiness gate still checked only worker HTTP health, not Kafka. In the Wave118 positive synthetic-worker test, **Kafka was deliberately unreachable** but the consumer returned **HTTP 200** as soon as the fake worker's `/_ready` probe passed. A consumer without a real Kafka partition assignment cannot consume the configured topic, so this remained a false readiness signal.

## Code changes

- `rust/ingestion-consumer/src/rebalance.rs`: add an `Arc<AtomicUsize>` to `RebalanceContext` representing actual assigned-partition count, initially zero. The **real rdkafka** `post_rebalance(Assign)` callback publishes the number of assigned partitions with Release ordering; `pre_rebalance(Revoke)` and `pre_rebalance(Error)` reset to zero. Keep all existing rebalance/offset hooks, and expose a cloned read-only-purpose assignment-count handle. The in-tree Rust callback unit test verifies count zero at start, two on assigning two partitions and zero on revoke, without altering original hook call counts.
- `rust/ingestion-consumer/src/consumer.rs`: expose the real Rust Kafka consumer context's assignment-count handle, avoiding fake Kafka health and avoiding a new topic/offset/poll behavior.
- `rust/ingestion-consumer/src/main.rs`: health HTTP server intentionally starts before the consumer is built. A shared `OnceLock<Arc<AtomicUsize>>` fail-closes readiness until the actual consumer installs its assignment-count handle. The `/_readiness` endpoint now requires **both** a currently routable worker with a verified successful HTTP probe **and** a real Kafka assignment count greater than zero; then delegates to the existing lifecycle shutdown readiness. `/_liveness` remains independent and always 200. No global lifecycle library change.
- Update Wave118's previously positive synthetic-worker-only probe and test to reflect the stronger Wave120 contract: a ready synthetic worker **without Kafka** must still produce readiness 503.
- Preserve Kafka group identity, callback ordering, batch/offset ACK state machine, wire protocol and all legal notices.

## Actual validation — October 26, 2026

Using the **actual first-party Rust ingestion-consumer source** patched into the temporary full Rust checkout, with original source files restored afterward:
- `cargo check --locked --offline -p ingestion-consumer --lib --bin ingestion-consumer --jobs 2` — **EXIT 0**
- `cargo build --locked --offline -p ingestion-consumer --bin ingestion-consumer --jobs 2` — **EXIT 0**, real ARM64 Mach-O executable.
- `python3 -m unittest -v tools.flind.test_native_consumer_kafka_group_wave119 tools.flind.test_native_ingestion_readiness_wave118` — **10/10 PASS** in 52.4 seconds, including a *real* Kafka 4.3.1 broker and *real* Rust consumer membership, plus an isolated **unreachable-Kafka + healthy synthetic HTTP worker** case. With unreachable Kafka, readiness **stays 503**; with a live Kafka group assignment and verified synthetic worker, readiness **reaches 200**. Both child services and temporary broker data are torn down.
- `cargo test --locked --offline -p ingestion-consumer --lib rebalance::tests::each_callback_reaches_its_hook_with_the_partitions` — **1/1 PASS**, confirming observable atomic assignment count zero → two → zero, and preserving the existing callback hook counts. The first attempt failed because the extended test recorded a second revoke before comparing the original one-revoke hook count; corrected test assertion order and retested PASS. This was a test harness correction, not a product code workaround.
- Git diff and Python syntax checks PASS. Mac retained ~12 GiB free, with offline Cargo and no paid cloud.

## Precise limits

**Qualified:** native Rust Kafka group assignment and verified synthetic HTTP worker jointly gate its HTTP readiness; no Kafka assignment or no verified worker means 503.

**Unqualified:** a synthetic HTTP worker has **no gRPC Node ingestion implementation**; the qualifying Kafka topic in Wave119 is intentionally empty. No real Rust Kafka event handling through the Node worker, ACK/retry/replay, committed offsets, durable product ClickHouse `events`, authenticated tenant-scoped API, Dashboard or OAuth/browser E2E has been qualified. The Kafka assignment-count signal is based on rdkafka's rebalance callbacks, so broker-loss detection follows its normal rebalance/session timeouts; it is **not** a per-request live TCP broker ping or a guarantee of immediate failure detection.

Keep Issue #82 OPEN, release NO-GO, repo private, inherited Actions disabled, no paid cloud, no release/deployment, third-party attribution untouched.
