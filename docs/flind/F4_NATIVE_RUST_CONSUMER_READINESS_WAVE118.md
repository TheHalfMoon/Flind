# Wave 118 — Fix native Rust ingestion-consumer false readiness without healthy workers

## Production defect observed in the real native binary

The first-party **Rust ingestion-consumer** executable built in Wave117 was started on an isolated local loopback port, with `KAFKA_HOSTS=127.0.0.1:65441` and `WORKER_ADDRESSES=http://127.0.0.1:65442` (no broker or Node ingestion worker running at either address). The **unmodified** binary returned **HTTP 200 from both `/_liveness` and `/_readiness` for eight consecutive samples**.

The shared lifecycle `ReadinessHandler` only checks whether the manager is shutting down. Separately, the Rust `WorkerRegistry` initializes each configured worker as optimistically `Healthy` before a real successful HTTP `/_ready` worker probe. A missing worker therefore caused a false Kubernetes readiness signal, even though ingestion could not deliver batches.

## Production fix

- `rust/ingestion-consumer/src/worker_registry.rs`: track `seen_successful_probe` per actual worker, false on registration and true only after a genuine successful HTTP `/_ready` probe; add `has_verified_routable_worker()`, requiring both a past successful probe and currently routable/eligible worker. Preserve the existing optimistic initial *routing* behavior and lifecycle shutdown semantics. Tests cover an unverified initial worker, a verified worker, unhealthy/removed worker and an empty registry.
- `rust/ingestion-consumer/src/main.rs`: guard the consumer's `/_readiness` route with `registry.has_verified_routable_worker()`; return **HTTP 503** unless a worker has passed an actual readiness probe, while continuing to delegate to the lifecycle readiness handler once one is verified. `/_liveness` remains independent.

The shared `common/lifecycle` library is not changed: its other consumers may legitimately have different readiness dependencies. No Kafka wire protocol, gRPC worker contract, OAuth, schema, credentials, donor notices or external services were changed.

## Executed evidence — October 26, 2026

The actual modified Rust source was copied **temporarily** into the existing full, original Git-backed Rust checkout for Cargo, leaving old full-checkout files restored after the build. The original `proto/ingestion/worker/v1/worker.proto` was available from Git (see Wave117).

```sh
cargo check --locked --offline -p ingestion-consumer --lib --bin ingestion-consumer --jobs 2
cargo build --locked --offline -p ingestion-consumer --bin ingestion-consumer --jobs 2
```

Both **exit 0**. The output is the genuine native **Mach-O arm64** first-party Rust ingestion-consumer binary.

```sh
python3 -m tools.flind.qualify_native_ingestion_readiness_wave118
```

**Exit 0, actual native HTTP proof**, using only local synthetic endpoints and two separately launched native-consumer sessions:
1. A synthetic worker responding `/_ready = 503` results in **15/15 real `/_readiness = 503` samples** while native `/_liveness = 200`.
2. A synthetic worker responding `/_ready = 200` results in the native consumer's `/_readiness` transitioning **503 → 200** after the real HTTP worker probe, while `/_liveness = 200`.
3. Both owned native consumer children and both synthetic localhost HTTP worker servers were terminated, and temporary files removed. The experiment **never** used a Kafka broker, accepted a real Node gRPC connection, or performed an offset commit.

```sh
python3 -m unittest -q \
    tools.flind.test_native_ingestion_readiness_wave118 \
    tools.flind.test_ingestion_consumer_rust_macos_wave117
```

**12/12 tests PASS**. Python compilation, Cargo compile/link, Bash and Git whitespace validations PASS; Mac retained ~12 GiB free, no paid infrastructure.

## Strict scope/release gates

**Qualified:** the actual native Rust ingestion-consumer binary compiles, links and serves a fail-closed worker-gated readiness endpoint, recovering when an actual (but synthetic) HTTP worker passes a readiness check.

**Unqualified:** real Kafka broker connectivity, Kafka offset assignment/commit, Rust consumer→Node gRPC worker batches/ACK, production Node worker startup, durable product events schema/materialized views, tenant-authenticated API, dashboard/browser, OAuth and full release. A **synthetic** HTTP `/_ready` worker is **not** the real Node.js worker. `release_qualified=false`; keep Issue #82 OPEN and Flind release NO-GO. Repository remains private, inherited Actions disabled, no publish/deploy and mandatory donor attribution preserved.
