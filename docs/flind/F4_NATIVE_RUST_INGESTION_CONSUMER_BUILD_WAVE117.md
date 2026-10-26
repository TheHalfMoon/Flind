# Wave 117 — Build native Rust ingestion consumer on Apple Silicon

## Actual production executable qualification (not a simulated Rust consumer)

The project contains a first-party `rust/ingestion-consumer` crate with its own library and executable, consuming Kafka events and sending batches to the Node ingestion worker over gRPC. The main Rust consumer source tree of the preexisting fuller `/tmp/flind-wave76-frontend` checkout was **verified byte-for-byte identical at the Git tree level** to the current Flind main revision; it was not substituted with a reimplementation.

Using the free, previously cached local Cargo dependencies and the same linker/SDK remediation introduced for Capture in Wave110:

```sh
cargo check --locked --offline -p ingestion-consumer --lib --bin ingestion-consumer --jobs 2
cargo build --locked --offline -p ingestion-consumer --bin ingestion-consumer --jobs 2
```

**Both commands completed with exit 0.** The linked actual executable is `Mach-O 64-bit executable arm64`, approximately **55 MiB**, and the Mac retained roughly **12.5 GiB free** after the build. The linked binary was **not started against any Kafka or worker endpoint** in this wave.

## Actual blocker recovered

The first `cargo check` failed in the **Protobuf code generator** because `proto/ingestion/worker/v1/worker.proto` was omitted by the **test checkout's sparse-checkout selection**. It did **not** mean the source file was absent from the Git repository. The 19 original tracked `proto/` files were included via `git sparse-checkout add proto`; the restored `worker.proto` Git blob SHA matched `HEAD`. The subsequent check compiled `ingestion-worker-proto`, `common-kafka-consumer`, `ingestion-consumer` and related crates and exited 0. No product source code or generated protobuf files were hand-authored.

## Reproducible admission helper

`tools/flind/check_ingestion_consumer_rust_macos_wave117.sh`:
- Only admits native Apple Silicon macOS with Cargo and Apple developer tools; refuses if full Rust workspace or the original tracked `proto/ingestion/worker/v1/worker.proto` is absent.
- Uses the host's installed SDK `CPLUS_INCLUDE_PATH` only for the subprocess, with no global installation or shell-profile changes.
- Requires at least **10 GiB** disk reserve before starting and runs offline, locked, max two Cargo jobs by default. Long builds should additionally be supervised while running.
- Default mode checks the **actual library and binary**. Optional `FLIND_INGESTION_CONSUMER_BUILD=1` compiles/links the executable.
- Accepts `FLIND_RUST_ROOT` and `CARGO_TARGET_DIR` so the Mac sparse main checkout can use an existing complete temporary Rust checkout safely.

The helper's cached offline `cargo check` returned **exit 0**. `tools/flind/test_ingestion_consumer_rust_macos_wave117.py` **7/7 tests PASS**: actual native linked Mach-O binary, main-versus-full-checkout source tree match, original protobuf Git blob parity, Rust/Node default Kafka topic and consumer group parity, guard behavior for missing proto, helper offline/config fields and Bash syntax. Python syntax and Git whitespace validation PASS.

## Release limits

This qualifies **native Rust ingestion-consumer code compilation and executable linking**, not a running ingest worker, Kafka offset commits, native consumer→Node worker gRPC, end-to-end event handling, product ClickHouse event tables or authenticated query API. No Node worker was installed or started; earlier pnpm offline bootstrap is blocked by missing locked tarballs and limited Mac disk space. The real Rust Capture→Kafka→ClickHouse Kafka Engine test (Wave114) is still a **temporary Memory-table integration**, not the product downstream ingestion worker.

The full Node ingestion worker, real Rust consumer API metadata/offset semantics, production ClickHouse schema, tenant authorization, dashboard/browser, OAuth and full release are **NOT qualified**, Issue #82 stays OPEN and release NO-GO. No paid cloud, public publication or deployment. Repository private, inherited Actions disabled, mandatory third-party attribution retained.
