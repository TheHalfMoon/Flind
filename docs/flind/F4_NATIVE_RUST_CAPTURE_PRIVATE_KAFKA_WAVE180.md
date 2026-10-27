# Flind Wave 180 — Actual cached Rust Capture HTTP → Kafka 4.3.1 with Redis 7.4.11

## Verified actual first-party binary smoke — 2026-10-27

**PASS:** real compiled first-party Flind **Rust Capture** process accepted a synthetic HTTP analytics event, ACKed its UUID, and a real Kafka consumer read back **that same UUID** from an isolated **Kafka 4.3.1** topic. The full Wave179 Kafka-to-ClickHouse Python synthetic relay also passed in the same owned broker lifecycle, but **the Rust-captured event was not forwarded into ClickHouse by the production consumer**. The two receipts are deliberately separate.

- Reused the **previously compiled, cached Rust Capture binary** at `/private/tmp/flind-wave110-rust-target/debug/capture`, exact SHA-256 `a255ae78e180d9488b4efc126b7d2c8378e209640ee36d7c28f491bb40693379`. Wave180 checks the digest before execution. **This does not prove that the binary was rebuilt from the latest Flind main commit.** It was compiled earlier, and its source provenance has not been fully re-established.
- Reused official locally cached **Kafka 4.3.1** and Kafka/Wave179's own **127.0.0.1-only** ephemeral broker, topic and isolated log directory (no Docker, external network or new download). Original Wave179 source now exposes an **optional private-broker probe callback**, leaving its default behavior unchanged.
- Reused a previously compiled **Redis 7.4.11** binary, a version **inside** the current Flind supported range of `>=7,<8`. Spawned on a newly selected loopback port, with empty snapshot schedule, AOF disabled, maxmemory 32MiB, and scratch-owned directory. This is separate from the prior Wave174/175 tests using incompatible Redis 8.10.
- Created a dedicated Kafka topic `flind_wave180_first_party_native_capture`; no other topics or real user data were written.
- Started cached Rust Capture with `CAPTURE_MODE=events`, `NOOP_SINK=false`, `PRINT_SINK=false`, Kafka producer destination explicitly pointing to the ephemeral loopback broker, exact dedicated topic, and Redis7 URL to the ephemeral loopback Redis port.
- Sent one fixed synthetic internal HTTP payload to **`/i/v1/analytics/events`**, with authorized **synthetic-only** bearer, generated UUID, synthetic distinct ID, and a fixed fake pageview path; the cached real Capture returned **HTTP 200** and an explicit per-UUID success acknowledgement.
- A real Confluent Kafka consumer with auto-commit disabled consumed a JSON record from the dedicated topic and validated **the exact acknowledged UUID, `$pageview` event, `flind-wave112-synthetic` distinct ID, and synthetic internal token**. Only after validation were offsets committed.
- The real private Kafka broker and the two private child processes (Capture and Redis7) were **stopped**. Wave179 additionally verified deletion of its exact marker-owned Kafka runtime scratch directory.
- The executable `tools/flind/qualify_cached_rust_capture_kafka_wave180.py` completed **exit 0** and reported `cached_rust_capture_to_real_kafka_qualified=true`, `native_capture_acknowledged=true`, `native_http_status=200`, `native_kafka_uuid_readback_qualified=true`, `native_redis_supported_version_qualified=true`, `owned_capture_stopped=true`, `owned_redis7_stopped=true`, `owned_kafka_process_stopped=true`, and `owned_kafka_scratch_removed=true`. Total elapsed approximately **27.9 seconds**.
- **17/17 focused Python guard/unit tests PASS** across Wave179 and Wave180 under `-W error::ResourceWarning`. The Wave180 tests verify fixed paths/fixture identity, loopback and scratch-marker admission, mismatched cached binary digest refusal and fail-closed promotion when a mocked native receipt is false.

## Qualified vs not qualified

This is a **real cached native Flind Rust Capture HTTP → real Kafka broker consumer roundtrip** and demonstrates more than synthetic CLI/Python Kafka producer/consumer alone. It **does not** imply:
- A freshly rebuilt or source-attested Rust binary from the **current** private GitHub main branch.
- Execution of Flind's **native Rust Kafka ingestion consumer** or actual Node gRPC worker; durable offset ACK/processing of real product events remains separate.
- Real Kafka materialized-view insertion or persistent ClickHouse storage of **this Rust-captured event**, let alone authenticated Flind API/dashboard readback. Wave179's adjacent Kafka→ClickHouse Memory relay consumes **its own separate fixed Python fixture**, not the Rust Capture topic.
- End-user/tenant authorization, cross-user security, SDK-to-dashboard browser/desktop E2E, persistence/recovery/retention, first-party OIDC/PKCE/JWKS, or shipping release readiness.

## Supported-version gate

The tests use supported **Redis 7.4.11** for native Capture. The separate ClickHouse Memory smoke in the Wave179 parent still uses local ClickHouse **26.10.2**, which exceeds Flind's current declared supported **`<=25.12`** range, so ClickHouse full product support is **not qualified**. No production service requirements were bypassed or changed.

**Issue #82 remains OPEN / Release NO-GO**, and branding/distribution issue #5 remains OPEN. Repo PRIVATE, inherited GitHub Actions disabled. No deployment/publishing, paid compute/models, customer data or alteration of mandatory third-party legal notices.
