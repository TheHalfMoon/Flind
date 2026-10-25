# Wave 101 — Live simultaneous 4-service qualification with exact Kafka→ClickHouse event SQL

## Goal

Prove that Flind can run **Apache Kafka 4.3.1, PostgreSQL 17.9, Redis 7.4.11 and ClickHouse 25.12.7.21 together**, against its **actual source version requirements**, on an 8 GiB Mac with a ~15 GiB free-disk reserve, and verify Django auth/session migrations while fixed Kafka messages reach real ClickHouse SQL. All services are local, temporary, disposable, owned by this test process, and bound to loopback.

Wave 95 had independently qualified Kafka→ClickHouse. Wave 72 had independently qualified PostgreSQL→Redis→ClickHouse. Until this Wave, those had **not run simultaneously**.

## Implemented

`tools/flind/qualify_four_native_services_wave101.py` composes the existing tested service wrappers and exact synthetic event relayer without adding cloud dependencies or running a real user's private data:
- Check exact Python direct dependency lock, source-level requirements and both selected native server binaries **before launching Kafka**. Refuse incompatible or missing tools.
- Launch an actual private Kafka KRaft broker and publish/consume exactly **three** fixed events from **two teams** with colliding distinct IDs.
- While Kafka is running, start a fresh private SCRAM PostgreSQL cluster and execute scoped Django contenttypes/auth/session migrations. This PostgreSQL cluster remains running for the rest of the proof.
- While PostgreSQL and Kafka are running, start isolated 64 MiB Redis (PING, SET, GET, DEL, no persistence), then isolated 512 MiB ClickHouse with loopback HTTP and temporary Memory tables.
- Independently check **the running** ClickHouse SQL `SELECT version()`; verify Redis and ClickHouse observed server versions, plus the actual PostgreSQL server version, against Flind's source specs.
- Replay only the exact Kafka-consumed test events into a temporary event table using the canonical source column names. Verify per-team aggregate, event counts, collision handling and cross-team property filters by real SQL; always drop the temporary table.
- Fail closed for malformed fixture, missing runtime, inconsistent component claims, unsupported versions and any unsuccessful real component proof.
- Leave all product-level truth fields **false**, including `production_capture_rust_qualified`, `production_sdk_http_qualified`, `production_kafka_ingester_qualified`, `production_events_schema_qualified`, `production_query_api_qualified`, `production_tenant_authorization_qualified`, `dashboard_e2e_qualified` and `release_qualified`.

## Actual evidence — October 25, 2026

On `macbook`, the exact selected versions were Apache Kafka **4.3.1**, PostgreSQL **17.9**, Redis **7.4.11** and ClickHouse **25.12.7.21**.

```sh
python -m tools.flind.qualify_four_native_services_wave101 \
  --kafka-home /tmp/flind-kafka-4.3.1/kafka_2.13-4.3.1 \
  --redis-bin /tmp/flind-wave74-services/redis-7.4.11/src/redis-server \
  --clickhouse-bin /tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64 \
  --json
```

**Actual exit 0**; receipt `four_native_services_synthetic_qualified=true`. All component checks, scoped Django auth, runtime versions, Kafka publish/consume, exact ClickHouse relay and team-scoped SQL readback passed. Temporary services cleaned up and ~15 GiB Mac free disk remained. No shared database was touched.

**37/37** regression cases pass (Wave 101 + Wave 72/85/95) with the test harness's controlled failure and success paths; Python byte compilation and whitespace checks pass.

The short-lived integration working tree had to overlay the updated Wave85 and Wave84 test tools onto an earlier Wave84 full-source checkout. The original Wave84 file was restored after testing and the two temporary untracked tools removed from that checkout. The committed harness source is based on current `main`, and can be run from a normal/current fully populated checkout.

## Boundaries

This proof uses the Kafka CLI and a test-owned relay into a temporary ClickHouse Memory table, not the production SDK, Django HTTP capture, Rust capture-rs receiver, background Kafka consumer, actual event tables, authenticated API query or visible Dashboard. Cross-team WHERE-clause filtering by a test is **not a tenant authorization test**. The three services' Django migrations include only scoped authentication/session apps here; a separate Wave96 isolated full-schema run with 3335 rows passed previously. Full end-to-end Flind production release remains **NO-GO** under Issue #82.

No paid service, public deployment, release, Github Actions re-enablement or removal of legally required donor notices.
