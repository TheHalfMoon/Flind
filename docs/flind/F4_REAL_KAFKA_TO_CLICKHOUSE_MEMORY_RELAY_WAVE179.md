# Flind Wave 179 — Real Apache Kafka 4.3.1 → ClickHouse local synthetic relay

## Actual completed qualification — 27 October 2026

**PASS: real isolated Kafka producer → real isolated Kafka consumer → bounded ClickHouse Memory INSERT and team-scoped SQL readback.** Unlike Wave177/178, which inserted hardcoded fixtures straight into ClickHouse, this test **reads the records delivered by a real Kafka broker** and only then performs the ClickHouse relay.

This is **not** a Flind SDK, Rust Capture, first-party ingestion worker, materialized view, authenticated query API/dashboard, or release qualification.

### Exact runtime evidence

- Existing, previously locally cached **official Apache Kafka 4.3.1** distribution at `/private/tmp/flind-kafka-4.3.1/kafka_2.13-4.3.1` was reused — **no new broker download**, Docker image, or paid service. JDK25 already installed.
- A **new KRaft cluster** was formatted into a unique private scratch subdirectory. Broker and controller listeners were configured for **127.0.0.1** ephemeral ports, using source Kafka config transformed through `isolated_config`. Auto topic creation explicitly disabled. Kafka JVM heap capped at 384MiB, and the helper enforces a separate **3GiB minimum free-disk reserve** and 500MiB scratch-broker-data budget (the older Wave84 safety helper retained its original 10GiB gate; it was **not** modified or silently patched).
- Created synthetic-only topic `flind_wave179_synthetic_only`. **Confluent Kafka Producer** sent the exact three Wave84 synthetic JSON records using `acks=all`, 10-second message timeout and explicit delivery callbacks; **all three ACKed**.
- **Confluent Kafka Consumer** joined a private synthetic-only group with `auto.offset.reset=earliest` and `enable.auto.commit=false`, consumed all three records, validated exact equality and order against the Wave84 fixture and committed the offsets only after validation. Two records had `team_id=101`, one had `team_id=202`. These are synthetic identifiers, not user-authenticated tenants.
- On validated Kafka readback, the probe verified the exact **Git-tracked first-party Flind `events_recent` HCL schema** (6 selected fields) at pinned private source commit `1905e9afb0f25f2685f042485b59f4c433403ffe`. Event fixtures were projected into the schema using explicit, synthetic UUIDs and timestamps.
- **ClickHouse local 26.10.2** ran a real `CREATE TABLE ... ENGINE = Memory`, `INSERT INTO ...` of exactly three Kafka-consumed synthetic records, plus five team-scoped queries, in a bounded scratch-only multiquery process with **stdin closed**. Team 101 returned exactly two records, team 202 one, and team 303 none.
- **Two real end-to-end tool runs PASS**, both exit 0; final exact proposed source reported `kafka_431_broker_qualified=true`, `real_kafka_producer_ack_qualified=true`, `real_kafka_consumer_qualified=true`, `local_clickhouse_relay_qualified=true`, `synthetic_kafka_event_count=3`, `synthetic_rows_inserted=3`, `clickhouse_sql_statements=7`, **`owned_kafka_process_stopped=true`**, **`owned_kafka_scratch_removed=true`**. Final run elapsed approximately **24.9s**.
- **9/9 Wave179 safety/unit tests PASS** under `-W error::ResourceWarning`, including exact fixture equality, adversarial/reordered/modified events refused, numeric team shape, non-loopback broker/refused, no secret env propagation, schema type drift rejection and synthetic topic/queue constraints.

The probe is stored as `tools/flind/qualify_real_kafka_to_local_clickhouse_wave179.py`. It **automatically stops its owned Kafka process group**, verifies the unique owned scratch marker before removing only that test broker's files, and marks release/product ingestion flags false even on synthetic transport success.

### Version compatibility blocker (separate)

Read-only inspection of `posthog/settings/service_requirements.py` on private Flind main shows **Redis `>=7.0.0,<8.0.0`** and **ClickHouse `>=24.8,<=25.12`** requirements. The local Redis8.10 and ClickHouse26.10 used in the previous partial smoke checks lie **outside these declared supported ranges**. The Wave179 Kafka transport/ClickHouse SQL check is a constrained engine smoke only; **it does not qualify ClickHouse26.10 for running the full Flind product or supersede the version requirement**. A supported ClickHouse version or independently justified, full-suite version-upgrade qualification remains an explicit release gate.

### What's still not qualified

- No **real Flind Rust Capture ingress**, actual Rust ingestion consumer, Node gRPC worker or ClickHouse materialized Kafka ingestion. The relay is intentionally a **Python synthetic bridge**.
- No persistent MergeTree table, cluster/retention/replay recovery, authenticated tenant lookup, Django API/dashboard, browser/desktop/mobile E2E or SDK workflow.
- Full PostgreSQL migrations/rollback, real Flind worker jobs, OIDC/PKCE/JWKS, branding and legal/distribution review remain open.

**#82 and #5 stay OPEN, release NO-GO.** Repo remains PRIVATE, inherited GitHub Actions disabled; no publication/deployment, paid models or external compute, no customer information, and legally required donor attribution preserved.
