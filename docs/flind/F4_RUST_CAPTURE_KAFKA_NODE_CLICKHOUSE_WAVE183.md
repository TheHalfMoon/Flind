# Flind Wave 183 — Native Rust Capture → Kafka → original TypeScript converter → ClickHouse UUID

## Actual integrated probe — October 27, 2026

**PASS:** a single acknowledged synthetic native **Rust Capture HTTP event** was consumed from real private Kafka4.3.1, passed through the **actual production Flind TypeScript `deserializeKafkaMessage()` function** running under local Node26, and inserted by a bounded synthetic test bridge into source-version-compatible **ClickHouse25.12.7.21 Memory** for an exact UUID readback. This runs a real TS adapter function but **does not** run the original production **Node gRPC worker** or native Rust Kafka ingestion consumer.

## Evidence and provenance

- Reuses the Wave182 single-event UUID continuity proof, Wave180 cached compiled Rust Capture pinned to the previous measured SHA256, Kafka4.3.1 ephemeral broker, **Redis7.4.11** (supported `>=7,<8`), ClickHouse25.12.7.21 (supported `>=24.8,<=25.12`) and Git-backed `events_recent` field schema.
- Newly added `tools/flind/inspect_native_kafka_node_wave183.mjs` imports **the exact first-party production TypeScript converter** `nodejs/src/ingestion/api/kafka-message-converter.ts`, rather than a mock or replacement reimplementation. The converter is **Git blob-verified** against the pinned source commit `1905e9afb0f25f2685f042485b59f4c433403ffe` at blob SHA `1a572256bc5616afd84919e46b0b39119e99fb80`. It has no runtime dependency on paid services; Node26 strips the TS type annotations.
- The Node probe receives only the Kafka-consumed and UUID-ACK-verified **synthetic** record and the exact approved Kafka topic. It checks source UUID, event, fixed synthetic token and distinct ID, and refuses client-supplied `team_id`, oversize input, unrecognized topic, malformed JSON and mismatched values. The actual `deserializeKafkaMessage` output is checked for Buffer, byte size, value equality, UUID/event/token/distinct-ID retention. Response contains only booleans, **no raw payload or credentials**.
- The new `tools/flind/qualify_native_capture_node_clickhouse_wave183.py` wraps the existing Wave182 actual native event bridge with an **optional Node gate, run before ClickHouse insertion**; default Wave182 behavior remains unchanged. If Node rejects or returns an invalid receipt, downstream ClickHouse insertion is prevented.
- **Real executable PASS**: `native_capture_kafka_node_converter_clickhouse_uuid_pass=true`, `actual_typescript_deserializer_uuid_verified=true`, `first_party_node_converter_source_verified=true`, `native_event_inserted_rows=1`, `owned_kafka_process_stopped=true`, `owned_kafka_scratch_removed=true`. Exit code **0**, elapsed approximately **43 seconds**. Rust Capture and temporary Redis were stopped as verified by the Wave182 parent gate.
- **45/45 Python unit/security tests PASS** across Waves179–183, `-W error::ResourceWarning`. Additionally, a direct native Node TS probe against an **unapproved Kafka topic** returned expected nonzero exit code **2**. Unit tests include source blob verification, real TypeScript transformation, wrong UUID, forged token, unauthorized `team_id`, absent Node, and false product/release gates.

## Scope and release blockers

This is a **one-event synthetic test chain**. The Kafka→ClickHouse hop is a direct Python bridge, and the TypeScript converter is invoked in a bounded standalone Node subprocess, **not the real ingestion worker service**. It uses a synthetic fixed token→team101 mapping for the fixture; it **does not prove real authenticated tenant isolation** or any SDK/browser behavior. The ClickHouse engine is **Memory, not persistent MergeTree/Kafka materialized view**.

**Still required:** actual first-party Rust Kafka ingestion consumer → Node worker over gRPC including ACK/offset frontier and retries; persistent ClickHouse delivery and query API; authenticated tenant separation; SDK→Dashboard/browser/desktop E2E; full PostgreSQL migrations/rollback, OAuth/PKCE/JWKS; current-main source-built native binary and final Flind-only artifacts/branding audit with required legal attribution.

Repository stays PRIVATE, inherited GitHub Actions disabled, no deployment or publication, no paid compute/models, no user data. **Release issue #82 and identity issue #5 remain OPEN / NO-GO.**
