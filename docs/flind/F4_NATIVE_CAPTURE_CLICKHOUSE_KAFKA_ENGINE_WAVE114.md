# Wave 114 — Real native Rust Capture → Kafka → ClickHouse Kafka Engine

## New integrated native milestone

Wave113 proved a real compiled **Rust Capture** service delivers a synthetic `$pageview` to a temporary Apache Kafka **4.3.1** broker, and a Kafka consumer reads back exactly the same UUID. Wave114 extends that *same real native event* to a temporary **ClickHouse 25.12.7.21** server using ClickHouse's built-in **Kafka table engine and a materialized view**.

No Python relay inserts the event into ClickHouse. There is **no manual SQL INSERT** to the event table. The actual integration follows:

`real Rust Capture-v1 HTTP POST → native rdkafka producer → real Kafka 4.3.1 topic → ClickHouse Kafka Engine subscriber → materialized view → ClickHouse Memory table → verified SQL readback`.

All services bind to loopback and run with synthetic payloads. The ClickHouse Memory table is **temporary and non-durable** and explicitly **not** the product `events` schema or production Node.js ingestion worker. There is no authenticated API or Dashboard in this proof.

## Actual results — October 26, 2026

Environment: Apple Silicon Mac, real linked 85 MB Rust Capture binary, native private Redis7, Apache Kafka4.3.1 and ClickHouse 25.12.7.21 binaries; no paid cloud, no Docker, no shared or external services.

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 -m tools.flind.qualify_native_capture_clickhouse_wave114
```

**Exit 0** with the following distinct qualifications passing:
- Real Rust HTTP service accepted a complete, synthetic first-party v1 capture event with per-UUID `result=ok`.
- Real Kafka native consumer read back the exact UUID/token/distinct ID/event type from Rust's native producer, not a CLI fixture.
- ClickHouse's **Kafka engine** subscribed directly to the same topic; its **materialized view** delivered exactly **one** event into a **Memory** table.
- SQL readback showed UUID/event/distinct ID/token identical to the Kafka record; an independent filter for an unrelated *synthetic* token returned **zero rows**. This is a test filter, **not proof of product authorization or tenant isolation**.
- Owned Redis/Rust/Kafka/ClickHouse processes were stopped and temporary data directories cleaned; Mac retained ~14 GiB free.

The first integration attempt failed because the locally supported ClickHouse **25.12** reports `Unknown setting kafka_auto_offset_reset` in the Kafka engine's SQL DDL. We removed this unsupported setting, and the subsequent real test succeeded, with **no manual offset resets or SQL event injection**.

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 -m unittest -v \
    tools.flind.test_native_capture_clickhouse_wave114 \
    tools.flind.test_native_capture_kafka_wave113 \
    tools.flind.test_ephemeral_kafka_wave84
```

**24/24 tests PASS**, including a new live **Rust→Kafka→ClickHouse** qualification plus safe rejection of non-loopback broker locators, foreign/malformed Kafka event fixtures, missing binaries, overlong/non-ASCII SQL, and backwards-compatible optional callback in Wave113. Python compilation and Git diff whitespace checks PASS.

## Changes

- `tools/flind/qualify_native_capture_kafka_wave113.py` extends the already-qualified helper with an **optional** `on_native_consumed(bootstrap, record)` callback, **only invoked after the actual native HTTP ACK and exact event Kafka consumer UUID readback**, preserving Wave113 default behavior.
- `tools/flind/qualify_native_capture_clickhouse_wave114.py` runs the complete bounded integrated local rig, using a ClickHouse Kafka engine, materialized view and Memory table, and checks both exact UUID and unrelated synthetic token filtering.
- `tools/flind/test_native_capture_clickhouse_wave114.py` contains live integration regression tests and explicit refusal tests.

## Boundaries / release NO-GO

This is **real Rust Capture → Kafka → ClickHouse**, but **not Flind's product Kafka ingestion worker**. The latter lives in `nodejs/src/ingestion` and relies on Node workspace dependencies, which were **not installed in the available sparse/full checkouts** on this Mac. Rehydrating the giant workspace would risk the remaining disk budget, and wasn't performed. The ClickHouse Kafka Engine / Memory table is a test-owned native bridge, not a substitution in product code.

Explicitly NOT qualified:
- Node.js production ingestion pipeline / offset, retry, person/group and transformations processing.
- Production `events` ClickHouse schema, materialized views, durable replicated tables.
- Authenticated, tenant-scoped API and browser Dashboard.
- OAuth/PKCE, tenant authorization, full frontend/desktop builds and release.

Keep Issue #82 OPEN and release NO-GO. Repo remains private with inherited GitHub Actions disabled; no public deployment, paid cloud or removal of required donor licenses.
