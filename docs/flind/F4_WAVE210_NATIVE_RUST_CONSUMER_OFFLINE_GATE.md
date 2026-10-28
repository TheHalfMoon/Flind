# Flind Wave 210 — Native Rust consumer offline qualification gate

## Purpose

Release qualification must distinguish a Cargo workspace that can read its
manifest and lockfile from one capable of **building and running** the actual
first-party Rust Kafka consumer and gRPC integration tests. The earlier
Wave190/191 exercises used a native Rust **test consumer** and test-only
ClickHouse/Node processing, not the original production consumer and
joined-ingestion pipeline.

This wave adds a **read-only, standard-library-only** preflight:

```sh
python3 -m unittest -v tools.flind.test_rust_consumer_offline_wave210
python3 tools/flind/qualify_rust_consumer_offline_wave210.py
```

The preflight checks:

- Original Flind first-party Rust consumer, gRPC transport, integration test,
  Cargo.toml and Cargo.lock are Git-tracked and match the current HEAD.
- `cargo metadata --offline --locked --no-deps` resolves the workspace's
  local manifests without network access.
- Every registry package in `rust/Cargo.lock` has a local, exact-version
  `.crate` archive whose SHA-256 matches the pinned Cargo.lock checksum
  (conservative complete workspace lockfile closure). Corrupt or same-named
  replacement archives are explicitly rejected.
- Separately reports unpacked source trees and whether those have vendor
  checksum metadata. Unpacked source alone does **not** imply a reproducible
  `cargo test --offline` build.

The gate returns exit 2 when blocked, exit 0 only if the offline input
preflight is satisfied. **Even a passing preflight is not a passing Rust
compile or runtime test.** No release qualification is granted by the gate.

## Evidence on 2026-10-28, Mac

First-party code from `main` at
`2641001815194fff621361bc97b31495de62f294` was checked on an isolated
Wave210 Git worktree. On this Mac:

| Gate | Observed result |
| --- | --- |
| Git source provenance | PASS: all checked files tracked and clean |
| Offline locked Cargo metadata | PASS |
| Registry package entries in Cargo.lock | 1,208 |
| Required `.crate` archives in local Cargo cache | 0 / 1,208 |
| Unpacked source trees with manifests | 1,207 / 1,208 |
| Unpacked sources with vendor checksums | 0 / 1,207 |
| Missing unpacked crate | `hotpath-drain-0.28.6` |
| First native `cargo test --offline --no-run` failure | `failed to download addr2line v0.25.1` |
| Actual production Rust consumer compiled/tested | **NO** |
| Original Rust/Kafka/Node joined pipeline/ClickHouse E2E | **NO** |
| Release | **NO-GO** |

A real bounded `cargo test -p ingestion-consumer --test
grpc_transport_test --offline --locked --no-run -j 2` was attempted.
It stopped in approximately one second with the above missing registry
archive, before native compilation. The test used an owned scratch
`CARGO_TARGET_DIR`, a 12 GiB free-space reserve, and a 270-second
safety cap. No network download or paid compute was used.

An exploratory attempt to point Cargo at the unpacked global registry
source also failed: those source trees lack `.cargo-checksum.json`,
so they are **not** a verified vendor directory. We did not fabricate
checksum files, overwrite the global Cargo cache, or claim the unverified
source meets the Cargo.lock integrity requirement.

## Next native qualification

Once exact Cargo.lock packages are legitimately available with
integrity checks, run the native integration tests **against the current
main source**, including real Kafka 4.3.1 and the original first-party
Rust transport/consumer, followed by the original production Node
joined pipeline and durable ClickHouse in an isolated synthetic fixture.
Require verified Kafka committed-offset/replay behavior, original Node
ACK after durable side effects, and secure tenant isolation tests.
Do not conflate the old test consumer/durable test driver with the
full production chain.

Native Node Jest also remains blocked on missing offline pnpm packages.
The browser/SDK, Django/auth and full-data-lineage release gates remain
open. Repository PRIVATE; Actions disabled; no deploy/publish.
**Release NO-GO.**
