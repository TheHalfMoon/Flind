# Flind Wave 181 — Supported-version real Kafka 4.3.1 → ClickHouse 25.12 synthetic relay

## Actual successful runtime result — 27 October 2026

**PASS:** version-admitted Apache Kafka4.3.1 real broker/producer/consumer to first-party-schema-backed ClickHouse local 25.12.7.21 Memory INSERT + scoped readback, with entirely synthetic event data, no network except Kafka's private loopback-only ephemeral ports.

Why Wave181 matters: Waves177–179 proved SQL and Kafka transport using **ClickHouse26.10.2** on the Mac. Flind's own `posthog/settings/service_requirements.py` declares ClickHouse `>=24.8,<=25.12`, so those engine successes **could not** establish version compatibility. A locally cached **ClickHouse25.12.7.21** executable was found at `/private/tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64` (official arm64 binary already present; no new download), and Wave181 tests it explicitly.

## Source version admission

`tools/flind/qualify_supported_clickhouse_kafka_wave181.py` uses a local-only, SHA1/256 Git-blob-digest-verified read of the **actual Flind tracked** `posthog/settings/service_requirements.py`. It statically parses `ServiceVersionRequirement(service="clickhouse", supported_version=">=24.8,<=25.12")` without importing or starting Django. An ambiguous or edited service requirement is refused. It interrogates the **actual executable** using `clickhouse --version`, validates bounded numeric version constraints with inclusive minor-line semantics, and refuses to start Kafka if the binary is outside source range. The check was run against pinned private source commit `1905e9afb0f25f2685f042485b59f4c433403ffe`, the verified historical baseline used in Wave171–180, **not a freshly qualified full current-main rebuild**.

Observed `clickhouse_observed_version=25.12.7.21`, `clickhouse_required_range=>=24.8,<=25.12`, `clickhouse_source_version_supported=true`. The standalone Memory-engine SQL INSERT using this supported version also passed separately: four synthetic records, seven actual SQL statements, two isolated teams, exit 0 in approximately 8.6 seconds.

## Actual Kafka-to-supported-ClickHouse proof

Reused the Wave179 bounded Kafka4.3.1 isolation helper and locally cached Kafka installation:
- Broker/controller on private 127.0.0.1-only ephemeral ports; KRaft cluster and logs only in marker-owned scratch, JVM max heap 384MiB; 3GiB free-disk reserve and 500MiB scratch Kafka budget. No paid resource or new Kafka download.
- Three fixed synthetic events published to the private Kafka topic, each ACKed by Kafka, independently consumed and checked by a real Confluent Kafka consumer with disabled auto-commit. One topic, one synthetic consumer group.
- Exact matched Kafka data projected into **first-party schema-verified** `events_recent` column subset (Git-verified HCL), loaded by SQL CREATE/INSERT into isolated **ClickHouse25.12 Memory engine**, then queried with validated `WHERE team_id` predicates. Team101=two events, team202=one, nonexistent team303=zero.
- **Real executable exit 0**, approximately **31.4 seconds**, `real_kafka_to_supported_clickhouse_synthetic_relay_qualified=true`, `real_kafka_producer_ack_qualified=true`, `real_kafka_consumer_qualified=true`, `clickhouse_inserted_rows=3`, `owned_kafka_process_stopped=true`, `owned_kafka_scratch_removed=true`.
- **17/17 Wave179 + Wave181 unit tests PASS** with `-W error::ResourceWarning`, including malformed/untrusted source version constraints, rejected ClickHouse26 version before Kafka startup, no successful result inferred from a forged/failed Kafka receipt, and false product/release gates even for a fully passing synthetic relay.

## Strict release interpretation

**This qualifies only the specific source-range-compliant synthetic SQL/Kafka relay**, not the full Flind product. In particular:
- ClickHouse is running **local Memory engine**, not durable MergeTree tables, native ClickHouse Kafka engine/materialized views, production cluster/shards, replay or retention.
- Wave180 verified **actual cached Rust Capture HTTP→Kafka** using a separate Kafka topic, but **that native event was not inserted into ClickHouse through the first-party ingestion consumer**. Kafka→ClickHouse in Wave181 still uses a Python synthetic relay. Cached Rust binaries have not been rebuilt from newest main.
- User-authenticated tenant isolation, SDK→API→Dashboard/browser/desktop E2E, full Postgres migrations and rollback, first-party ingestion worker and source/package/installer identity audit remain pending.
- Redis7.4.11 used for Wave180 native Capture is in source-supported Redis `>=7,<8` range; previously tested Redis8.10 cannot be treated as a fully supported Flind deployment version.

**Issues #82 and #5 remain OPEN; Release NO-GO.** Repo stays PRIVATE with inherited GitHub Actions disabled, no publishing/deployment, paid compute or customer data, and mandatory legal attribution preserved.
