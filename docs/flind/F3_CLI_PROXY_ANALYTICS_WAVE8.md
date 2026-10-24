# F3 Wave 8 — isolate inherited Node CLI analytics env

## Risk and fix

Flind's Rust CLI embedded a Node API CLI and automatically supplied a
source-provider analytics host and build-time token, even where the user
had not configured any external analytics service. It also propagated an
invocation identifier intended to join Rust and Node telemetry.

This wave removes the inherited analytics URL and build-time analytics-token
injection. The Node child now explicitly excludes these inherited environment
variables, even when they appear in the parent's environment:

- `POSTHOG_ANALYTICS_API_KEY`
- `POSTHOG_ANALYTICS_HOST`
- `POSTHOG_CLI_INVOCATION_ID`

User-scoped API credentials (`POSTHOG_CLI_API_KEY`, project ID and host)
remain available so ordinary authenticated CLI operations are not removed.
Renaming those older protocol environment variables requires independent
API/bundle migration and end-to-end tests.

## Tests and residual risks

- Python static regression checks protect the source and credential-injection
  contract.
- Rust unit test validates the actual `std::process::Command` child
  environment edits, including preservation of a user API key.
- `rustfmt --check` validates formatting.
- Full Cargo compile/test requires the original CLI dependency set, missing
  from the current offline Cargo cache; this source change alone does NOT
  qualify the actual Node bundle, which may contain other telemetry defaults.

**Critical:** this is an analytics-env boundary, not a guarantee that no
network request leaves a system. The Node JS bundle, Rust-side telemetry,
inherited API hosts, updater artifacts and real DNS/HTTP egress still require
runtime tests on supported OSes. Release remains **NO-GO**, private, no
deployment.

## Requalification on 2026-10-24

The public Cargo dependency cache was populated and the actual CLI crate
compiled. Rust caught a regression in the new `Command::get_envs()` test:
`name` must be dereferenced before comparison with a string. Wave 11
fixes both comparisons.

After this fix, the complete Rust CLI test suite passed using:

```bash
CARGO_BUILD_JOBS=2 CARGO_PROFILE_TEST_DEBUG=0 CARGO_INCREMENTAL=0 \
  cargo test --manifest-path cli/Cargo.toml --locked --offline --all-targets -- --test-threads=2
```

**337 Rust tests PASSED** (255 library + 13 debug-symbol + 13 git +
28 integration + 28 sourcemap; binary entrypoint has zero tests). Rust
compilation and integration are now source-qualified on macOS arm64.
Cross-OS CLI packaging, API proxy real network egress, auth issuance
and full product release are NOT qualified.
