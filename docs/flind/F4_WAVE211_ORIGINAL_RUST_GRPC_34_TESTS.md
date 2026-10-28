# Flind Wave 211 — First-party Rust gRPC transport tests, 34/34 PASS

## Qualification achieved

For the first time in this local sequence, the **original Flind Rust
`ingestion-consumer` gRPC transport integration test binary** was
compiled and executed successfully against the current `main` source.

The WSL checkout uses Git SHA
`04cbb29c61bbe359ddfe46b626804e02b29cbe6f` (Wave210).

```text
Original Rust test target: ingestion-consumer/tests/grpc_transport_test.rs
Binary: original Cargo test target (not a JavaScript simulation)
Tests passed: 34
Tests failed: 0
Process exit code: 0
Cargo offline locked metadata: PASS
Original first-party Git source attestation: PASS
```

The 34 tests exercise the original Rust gRPC transport against its
**first-party mock WorkerIngest service**, including ordered chunk
delivery, out-of-order ACK correlation, partial acceptance, fencing and
replay on failure, watchdog behavior, and worker reconnection.

This is **not** a test against the production Node joined analytics
worker or ClickHouse and does **not** prove a real Kafka broker
consumption/commit boundary. A complete Rust → Kafka → Node →
ClickHouse release E2E remains outstanding.

## How this local blocker was resolved safely

Previous Mac Wave210 preflight reported no locally cached `.crate`
archives for the 1,208-entry Rust workspace Cargo.lock. Windows/WSL
had a different Cargo cache and much more available disk space.

- Reused the already configured **Windows GitHub CLI** authorization
  to clone Flind privately into an isolated WSL source checkout. No
  secret/token was copied or written into the repository.
- Fetched free public Rust crates with `cargo fetch --locked
  --target x86_64-unknown-linux-gnu`. Following that, the
  architecture-specific Rust test build ran **fully offline**.
- A first build attempted the original Rust test but failed before
  running tests because `protoc` was absent.
- Extracted Ubuntu's signed `protobuf-compiler`,
  `libprotoc32t64`, and `libprotobuf32t64` packages (3.21.12)
  into the test-owned WSL directory
  `~/work/Flind-wave211-protoc`, without `sudo`,
  changing global system packages, or moving user files.
- Set only the test-process `PROTOC` and
  `LD_LIBRARY_PATH` environment variables. The original
  `ingestion-worker-proto` build then succeeded and the
  native gRPC integration suite returned **34/34 PASS**.

The conservative Wave210 **full workspace** offline-archive gate
can still report incomplete closure for platform-specific packages.
Wave211 directly executed the actual Linux target-specific Cargo
test, so its positive verdict comes from **the real test binary**,
not an inference from cache inventory.

## Repeatable native qualifier

```sh
export PROTOC="$HOME/work/Flind-wave211-protoc/local/usr/bin/protoc"
export LD_LIBRARY_PATH="$HOME/work/Flind-wave211-protoc/local/usr/lib/x86_64-linux-gnu"
python3 -m unittest -v tools.flind.test_native_rust_grpc_transport_wave211
python3 tools/flind/qualify_native_rust_grpc_transport_wave211.py
```

`qualify_native_rust_grpc_transport_wave211.py` verifies
original source attestation, offline/locked Cargo metadata,
refuses unowned or symlinked build destinations, runs the
**actual** Rust gRPC integration test with two Cargo jobs and
two Rust test threads, bounds its run time and free-space usage,
parses the native test result, and returns nonzero on failure.
It explicitly sets `CARGO_NET_OFFLINE=true`; no paid inference,
remote runtime, product/customer data, or publication is involved.

Regression tests for this qualifier: **4/4 PASS**. They cover
real Rust output parsing, false-success rejection, owned target
directory enforcement, and symlink rejection.

## Remaining release gates

- Real Kafka broker → **original** Rust consumer group/commit and
  replay under crash/failover conditions.
- Original production Node `createJoinedIngestionPipeline` with
  first-party gRPC server and durable ClickHouse processing,
  acceptance only after the full side-effect barrier.
- Full native Node Jest dependency qualification.
- Django/authenticated tenant isolation, SDK/browser native E2E,
  product acceptance, and full release readiness.

Flind remains PRIVATE, GitHub Actions disabled, no deployment or
publication. **Release NO-GO.**
