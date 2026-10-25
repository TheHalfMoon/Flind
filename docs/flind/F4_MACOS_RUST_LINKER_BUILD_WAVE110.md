# Wave 110 — Native Apple Silicon Rust Capture build-check qualification

## Two real host toolchain defects identified

The inherited `rust/.cargo/config.toml` unconditionally appended `-C link-arg=-fuse-ld=lld` for `aarch64-apple-darwin`. On a standard Apple Command Line Tools host without `ld64.lld`, the actual `cargo check --locked -p capture --lib` failed immediately while linking the first build scripts:

```
clang: error: invalid linker name in argument '-fuse-ld=lld'
```

After temporarily overriding this flag without modifying the project, Cargo progressed through dependencies including SQLx, Axum and OpenTelemetry; the first 180-second attempt timed out without any new linker error. When we tested the revised config directly, `rdkafka-sys` surfaced a separate macOS SDK include search problem: Apple's default `g++` was unable to find `<string>` and `<iostream>` even though the C++ libc++ headers were installed inside the active `xcrun --show-sdk-path` SDK. A standalone C++ compile failed with exit 1; it passed (and the binary ran) when child-process-only `SDKROOT` and `CPLUS_INCLUDE_PATH` pointed at the installed SDK's `usr/include/c++/v1`.

## Changes to Flind

- `rust/.cargo/config.toml` no longer forces unavailable optional `lld` on all Apple Silicon hosts. `[build].rustflags = ["--cfg", "tokio_unstable"]` remains workspace-wide. The existing offline SQLx and AWS entropy environment settings remain unchanged.
- `tools/flind/check_capture_rust_macos_wave110.sh` provides a reproducible **offline**, source-local, no-paid-service check on Apple Silicon. It discovers macOS SDK through `xcrun`, sets `SDKROOT` and `CPLUS_INCLUDE_PATH` **for the child process only**, and checks **both** the Capture Rust library and binary targets. It supports `FLIND_RUST_ROOT` for a full checkout when the current main checkout is sparse and preserves any user-supplied `CARGO_TARGET_DIR`. It does not mutate global developer settings or touch user credentials.
- `tools/flind/test_mac_rust_linker_wave110.py` tests the platform Cargo flags, retained Tokio/SQLx/AWS settings, actual native `rustc` executable link/run, actual C++ include/compile/run with explicit installed macOS SDK, and offline wrapper behavior.

## Actual evidence — macbook, October 26, 2026

1. **Dependency graph successfully resolved:** `cargo metadata --locked --format-version 1` returned **exit 0**, 80 workspace members and 1,288 packages. A previous offline-only attempt had failed because an unrelated workspace Git dependency `js-source-scopes` was uncached. Initial one-time downloads were free and used no paid service.
2. **Production-source identity verified:** The `rust` tree Git hash was identical between the full Rust source checkout and latest Flind main before the config edit: `85a3a59d20eaf6d39045ded85d35a8dd6f2001f6`. Capture source hash itself was `5311f8869f8101ac558855c11bba51622979dd46`. The Cargo check therefore covered the same native Rust source rather than stale Rust code.
3. **Actual Rust library qualification:** With the revised config and child-only macOS SDK C++ paths, `cargo check --locked --offline -p capture --lib --jobs 2` returned **exit 0**. Logs include `Checking common-kafka`, `common-types`, `common-ingestion-warnings`, `capture`, and `Finished dev profile`. The test is **compilation/check only**; no Rust server execution.
4. **Actual Rust binary qualification:** The same command with `--bin capture` returned **exit 0**.
5. **Reusable helper verification:** From an unmodified full Rust tree except the same revised Cargo configuration:
   ```sh
   FLIND_RUST_ROOT=/path/to/Flind/rust \
   CARGO_TARGET_DIR=/tmp/flind-capture-target \
   bash tools/flind/check_capture_rust_macos_wave110.sh
   ```
   The helper checked both `--lib --bin capture` with **exit 0**, offline, after dependency compilation.
6. **20/20** focused Wave109 + Wave110 tests PASS, including native macOS Rust and C++ standalone compiled executable smoke tests, Python compilation and whitespace checks PASS.
7. Build intermediates were capped to local temp storage (about 849 MiB of debug/check output) and the Mac retained roughly 16 GiB disk space free. No global linker, SDK or shell-profile change.

## What this qualifies — and what it does not

**Qualified:** Native offline Cargo **check** for the actual Rust `capture` library and binary targets using a fixed Mac build environment. Source parity guard from Wave109 also PASSES. The forced linker and SDK header blocker were both diagnosed with native repros and locally resolved.

**Not qualified:** `cargo build` producing a fully linked runnable Capture binary, Rust unit/integration tests, starting a Capture server, full production Kafka publish/consume from the server, real ClickHouse product-schema ingest/readback, authenticated multi-tenant API, dashboard/browser E2E, OAuth/PKCE, frontend/desktop distributions, or release. Issue #82 stays open; release remains NO-GO.

Project constraints: private GitHub repository, inherited GitHub Actions disabled, no publishing/deployment, no paid cloud, and preserve mandatory third-party legal attribution.
