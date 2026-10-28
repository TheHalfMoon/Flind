# Flind Wave 212 — Original Rust consumer commit and replay against real Kafka 4.3.1

## Native qualification

Wave211 qualified the original `ingestion-consumer` gRPC transport with
**34/34 native tests**, but against a first-party mock gRPC worker and
without a real Kafka broker. Wave212 extends the evidence to the original
Rust **Kafka consumer, topic-offset ledger, replay and crash/recommit
path** using an isolated, real Apache Kafka 4.3.1 KRaft broker on
`127.0.0.1:9092`.

Original first-party integration suite:
`rust/ingestion-consumer/tests/e2e_integration_test.rs`.

Three native original-source cases, each exercised in an actual Rust
test binary against a live Kafka broker:

1. `the_committed_offset_is_the_ledger_frontier`: no offsets can
   be committed beyond the ledger's contiguous acceptance frontier.
2. `a_partial_ack_redelivers_only_the_unfinished_messages`: a partial
   acknowledgement carries forward the unfinished messages for replay.
3. `consumer_crash_before_commit_redelivers_without_loss`: a crash
   before offset commit causes safe redelivery rather than silent loss.

A first-party Kafka smoke qualifier also publishes and consumes
three synthetic events with colliding distinct IDs across two team
identities. The actual native Rust tests use their own synthetic test
messages and first-party mock gRPC workers.

## Reproducible local invocation

```sh
export PATH="$HOME/.cargo/bin:$PATH"
export JAVA_HOME="$HOME/work/Flind-wave212-runtime/java"
export PROTOC="$HOME/work/Flind-wave211-protoc/local/usr/bin/protoc"
export LD_LIBRARY_PATH="$HOME/work/Flind-wave211-protoc/local/usr/lib/x86_64-linux-gnu"

python3 -m unittest -v tools.flind.test_original_rust_kafka_wave212
python3 tools/flind/qualify_original_rust_kafka_wave212.py
```

The qualifier verifies Git HEAD provenance of the original Rust
`ingestion-consumer`, its integration suite and Cargo.lock; runs
`cargo metadata --offline --locked`; requires the project-owned Kafka
runtime marker; verifies the Kafka distribution archive against the
official SHA-512 digest; starts KRaft on loopback only with synthetic
data and a private ephemeral storage directory; runs the three
**actual** native Cargo test cases with offline locked dependencies;
and checks the broker port and scratch data were released afterward.

The Kafka runtime is based on the verified Apache Kafka 4.3.1
distribution. Java uses Temurin JRE21 (21.0.13+9); the local
`protoc 3.21.12` and libraries were extracted from official Ubuntu
packages. None were installed system-wide and no `sudo` was used.
The Rust test target reuses the marker-owned Wave211 WSL build cache
to avoid disk and CPU waste. No paid cloud, real customer data or
production services were involved.

The test fixture hardcodes Kafka `localhost:9092`; to prevent use
of another service, the isolated broker qualifier checks that port
availability before binding, runs only one private broker, and waits a bounded
10-second interval for port release after KRaft shutdown. An active listener
or leftover private temporary storage fails the gate closed.

## Scope and release boundaries

**What this qualifies:** The original first-party Rust consumer
integration tests for Kafka offset frontier, partial-ACK redelivery,
and crash-before-commit recovery with a real local Kafka broker and a
test gRPC WorkerIngest implementation. This extends Wave211's transport
qualification with an actual Rust/Kafka consumer integration.

**What remains NOT qualified:**

- Original **production Node** `createJoinedIngestionPipeline` under the
  actual Kafka/Rust flow; the worker for these Rust tests is a mock.
- Production durable ClickHouse event persistence, transaction/ACK
  ordering across Kafka/Node/CH and tenant-authenticated readback.
- Complete native Node Jest dependency tree, Django/auth/tenant
  isolation, SDK/browser E2E, product acceptance and release.

Flind is PRIVATE, GitHub Actions remain disabled, and there is no
deployment or publication. **Release NO-GO.**
