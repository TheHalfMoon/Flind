# Wave 116 — Real Rust Capture → Kafka → first-party Node TypeScript adapter

## What the test actually executes

Building on Wave113's real native Rust Capture `rdkafka` producer and Kafka 4.3.1 broker, `tools/flind/qualify_rust_kafka_node_bridge_wave116.py` uses the existing ephemeral Kafka fixture to obtain an **independently Kafka-consumed synthetic record** with the exact event UUID, event name, distinct ID, and synthetic capture token that the real Rust server acknowledged.

Once that native Kafka-consumer receipt has passed, a scoped callback sends the parsed record through `tools/flind/inspect_node_kafka_event_wave116.mjs`. This uses **Node 26's built-in TypeScript type stripping to import and execute the actual production `nodejs/src/ingestion/api/kafka-message-converter.ts::deserializeKafkaMessage` function**, including Wave115's empty-buffer/tombstone correction.

The Node subprocess checks that the produced Kafka event's UUID, event type, synthetic distinct ID, synthetic token and byte counts remain correct after conversion into the actual `node-rdkafka`-compatible message shape. It outputs only sanitized pass/fail predicates. All child services and temporary broker state are stopped and cleaned after testing; no external or customer data is involved.

**Critical evidence distinction:** The test constructs the `SerializedKafkaMessage` *envelope* from the real Kafka record, using a synthetic null key and empty headers, because it **does not run the product Rust Kafka consumer gRPC/HTTP service** that normally constructs this envelope. It therefore proves conversion of **the actual Kafka event data** in the first-party Node adapter, **not** correctness of the end-to-end Rust-consumer envelope, Kafka key/header metadata, batch/offset acknowledgement, or the Node ingestion worker.

## Evidence — October 26, 2026

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 -m tools.flind.qualify_rust_kafka_node_bridge_wave116
```

**Exit 0.** All three distinct stages verified: real Rust HTTP Capture per-event acknowledgment, independent actual Kafka 4.3.1 UUID readback, and real production TypeScript Node adapter execution with UUID and synthetic event metadata preservation. `real_rust_capture_to_kafka_to_node_adapter=true`.

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 -m unittest -q \
  tools.flind.test_rust_kafka_node_bridge_wave116 \
  tools.flind.test_native_capture_kafka_wave113
```

**14/14 tests PASS** with a second complete live Rust→Kafka→Node-adapter run, direct TypeScript adapter tests, foreign event/token/topic and bogus UUID refusal, missing binary guard, oversized fixture refusal, and explicit release-NO-GO predicates. Python compilation and Node syntax checks PASS.

## Offline Node workspace admission and disk safety

The attempt to install a **filtered actual Node workspace dependency closure** with pnpm 11 from the existing Mac cache was deliberately run **offline, frozen-lockfile and with scripts disabled**, guarded by a **135-second timeout and an 11 GiB minimum free-disk reserve**. It resolved approximately **2,166 packages**, reused approximately **1,298** packages and downloaded **zero**. It could not finish because the local cache lacks the exact locked tarballs `@types/node@10.17.60` and `@amplitude/ua-parser-js@0.7.33`, among potentially others. The bounded run was terminated and only the new root `node_modules` tree created by this attempt in the *older temporary test checkout* was cleaned. The actual Flind main checkout remained unchanged. The Mac retained roughly **13 GiB free** after cleaning. No internet npm fetch was attempted, no paid cloud, and no claim of full dependency closure.

## Remaining qualification gates

- Production Rust Kafka consumer API → real serialized Kafka message (including actual headers, key, partition, offsets and replay semantics) → full Node ingestion worker.
- Actual Node downstream processing and durable **production** ClickHouse `events` schema; Wave114's Kafka Engine → Memory materialization is a temporary native integration fixture, **not** the production ingestion worker.
- Authenticated, tenant-scoped product query API → Dashboard/browser E2E.
- OAuth/PKCE, frontend/desktop qualified builds, repository/distribution branding, and complete release gates.

All `production_node_ingestion_worker_qualified`, `real_rust_grpc_consumer_api_qualified`, `real_production_clickhouse_ingestion_qualified`, `tenant_query_api_qualified`, `browser_dashboard_e2e_qualified` and `release_qualified` predicates remain deliberately **false**. Keep GitHub Issue #82 OPEN, repo private, inherited Actions disabled, no publication/deployment and preserve required donor attributions.
