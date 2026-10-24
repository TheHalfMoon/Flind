# F3 Wave 11 — real Rust CLI test qualification and compile fix

## Compiler finding

A previous first-party Rust test used `name == key` while iterating
`Command::get_envs()`. The iterator gives a borrowed OsStr name, so
comparing a borrowed reference directly to a Rust string failed with
`E0277`. Fix both comparisons to dereference `*name`. The code under
test, which removes inherited analytics environment settings, is unchanged.

## Executed evidence, macOS arm64, 2026-10-24

- Cargo dependencies fetched from the public registry using the existing
  `cli/Cargo.lock`. No paid cloud or GitHub Actions.
- `cargo test --manifest-path cli/Cargo.toml --locked --offline --lib`:
  **255 PASS**.
- `cargo test --manifest-path cli/Cargo.toml --locked --offline --all-targets`:
  **337 PASS**, comprising library (255), binary (0),
  debug-symbol tests (13), git tests (13), integration mod tests (28)
  and sourcemap tests (28).
- `rustfmt --check cli/src/api_proxy.rs` **PASS**.
- Python/Flind regression suite previously checked **177 PASS** on
  this same main frontier. Re-run after the merge for final evidence.

## Important limitations

Passing these tests does not prove live OAuth/device-code issuer ownership,
real API ingestion, network egress, local first-run experience, backend,
frontend/browser tests, Windows/Linux support, first-party signed
distribution, or full zero-identity. These remain mandatory release gates.
Maintain private repository and disabled inherited Actions. No deployment.
