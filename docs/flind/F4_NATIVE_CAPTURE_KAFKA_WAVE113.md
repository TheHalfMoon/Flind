# Wave 113 — ACTUAL native Rust Capture → local Kafka 4.3.1 → consumer event readback

## This wave replaces the synthetic Kafka-producer-only proof

The code in `tools/flind/qualify_native_capture_kafka_wave113.py` starts a **real temporary Apache Kafka 4.3.1 broker** on `127.0.0.1`, a real ephemeral Redis instance, and the **compiled real Rust Capture binary** built in Wave110. Unlike earlier Waves 95/101 (which sent synthetic JSON to Kafka using the Kafka CLI), this wave uses **Rust Capture's own production `rdkafka` producer to publish the event**.

The check uses actual product code in `rust/capture` with `NOOP_SINK=false`, `KAFKA_INGESTION_PRODUCER_METADATA_BROKER_LIST=127.0.0.1:<private port>`, a freshly created one-partition `flind-wave113-native-analytics` Kafka topic, and `CAPTURE_OUTPUT_ANALYTICS_MAIN_TOPIC` pointed exactly at it. No external hosts, cloud services, inherited tokens or user data. The test sends a fully formed synthetic `$pageview` event via an actual native HTTP POST containing the required Flind SDK headers and synthetic token.

**Two independent receipts are required**:
1. The Rust Capture HTTP reply must be 200 and include **`results[<sent UUID>].result == "ok"`**. A mere HTTP 200 is never enough.
2. The **actual Kafka console consumer** reads exactly one message from the temporary native topic; that record must have the **identical event UUID**, `event="$pageview"`, `distinct_id="flind-wave112-synthetic"` and `token="flind_synthetic_internal_token"`. This Kafka record is not an event that the Kafka CLI produced: the CLI synthetic fixture uses a **different topic**, exercised before the native round-trip callback.

All brokers, native Capture/Redis processes, and test data are temporary. The existing Kafka4.3.1 ephemeral qualification accepts an **optional** `on_broker_ready(bootstrap)` callback, in addition to the original `on_consumed(records)` hook, so existing Wave84/95/101 callers retain their original behavior. No application protocol names, product migrations or donor notices were changed.

## Actual evidence — October 26, 2026

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 -m tools.flind.qualify_native_capture_kafka_wave113
```

**Exit 0.** `actual_native_rust_capture_to_real_kafka=true`, `isolated_kafka_431_passed=true`, native Rust HTTP bound, per-event UUID ACK correct, exact payload read back from Kafka, Redis local PASS, no-op sink disabled, owned Capture and Redis stopped, ephemeral Kafka stopped by the underlying Kafka rig. Mac retained ~14 GiB free.

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 -m unittest -v \
    tools.flind.test_native_capture_kafka_wave113 \
    tools.flind.test_ephemeral_kafka_wave84
```

**17/17 PASS**, exit 0, including the real native Kafka round-trip and regression tests verifying the older Kafka helper still works and handles failures/cleanup. Python compilation and Git whitespace checks PASS.

## Strict release boundary

**Qualified:** Native Rust Capture runtime → true Kafka producer → native Kafka broker → consumer readback of the exact synthetically generated event UUID. Earlier Wave111/112 native HTTP NOOP testing remains valid independently.

**Not qualified:** The production Flind **Kafka-to-ClickHouse ingestion worker**, actual `events` table schema and materialized views, authenticated multi-tenant query API, Dashboard/browser E2E, OAuth or release. **Manual Kafka-to-ClickHouse relay from previous waves is explicitly not equivalent to production ingestion.** `production_clickhouse_ingestion=false`, `production_query_api=false`, `tenant_auth_end_to_end=false`, `dashboard_browser_e2e=false`, `release_qualified=false`. Keep Issue #82 open.

No publishing, release, inherited GitHub Actions activation, paid providers, shared databases, real customer data or removal of third-party license attribution.
