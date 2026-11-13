# Release-grade Flind CLI Node bundle policy

Status: **source gate and native Rust regression are added; exact-head CI
must pass before merge. This is not authorization for a public release.**

## Finding

The Rust CLI delegates its `api` command to a separate Node JavaScript
bundle. Earlier hardening validates the parent origin and refuses
nested host/config flags and inherited JavaScript preload options.
But `find_script()` historically also accepted a path supplied by
`POSTHOG_API_CLI_PATH` or discovered an old file under a writable
legacy installation directory. The arbitrary script receives the
user's CLI API credentials.

## Release safety boundary

- **Release/optimized builds** (`not(debug_assertions)`) can only
  execute bytes embedded at compilation time by `cli/build.rs`.
  The build script's exact `include_bytes!` source remains the
  executable source of truth.
- If no Node bundle was embedded, the release CLI's `api` command
  **fails closed** with the existing `BundleNotEmbedded` error. It
  does not read a legacy provider's file or honor an environment
  override to restore functionality.
- Only **debug/development builds** retain the synthetic-script
  override and legacy-path compatibility to support isolated local
  CLI subprocess tests and development. These are **not release
  paths** and must never be shipped as product binaries.
- Each release invocation rewrites the included bytes into the
  versioned local script path before spawning Node. A future
  signing/secure-file-write, symlink/race and runtime outbound
  network audit is still needed. This does **not** prove arbitrary
  Node bundle internals are secure.

## Tests

Native Rust unit cases assert that a legacy JS file cannot rescue
an unembedded release bundle and that the release helper reads the
exact embedded bytes. Existing debug CLI integration tests must
continue passing. The new lightweight CI checks that the production
`find_script` configuration contains only the embedded-bundle path,
that synthetic overrides are debug-only and that `cli/build.rs`
uses exact byte embedding.

This intentionally blocks the public `api` command until an
independently qualified Flind-owned Node API bundle is embedded.
The rest of Flind CLI and the web application are not changed.

No GitHub Release, tag, public installer, binary, SDK package or
production deployment until the explicit owner's `GREEN LIGHT FLIND`.
Retain third-party source license and copyright notices.
