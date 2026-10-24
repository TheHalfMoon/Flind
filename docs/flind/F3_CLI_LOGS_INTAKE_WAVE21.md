# F3 Wave 21 — Logs import egress containment

## Threat boundary

The CLI's experimental Loki importer accepts an explicitly provided project
write key and a host resolved from CLI configuration. An old saved login
could still hold the imported vendor's cloud host. A redirect from a configured
intake may also cause credentials to cross an unintended network boundary
if automatically followed.

## Changes

- Validate the logs intake *origin* before constructing the API route.
- Reject the inherited provider's apex and subdomains as intake destinations.
- Require HTTPS for remote destinations, with a loopback-only HTTP exception
  for local development; reject embedded credentials, query, fragment, or
  non-root path in the configured intake base URL.
- Construct the route using a URL parser, preserving explicit ports.
- Disable automatic redirects for the Loki import and dry-run HTTP clients.
- Retain the historical POSTHOG_PROJECT_API_KEY variable name only as a
  CLI compatibility contract. A separate variable migration needs user
  and documentation coverage.
- Preserve arbitrary explicitly configured, HTTPS-protected Flind/self-hosted
  domains; no new vendor destination or cloud dependency.

## Evidence and limits

- Rust unit tests cover allowed TLS/loopback cases and forbidden vendor,
  non-root-path, query, fragment, userinfo and remote plaintext examples.
- Python source-structure regressions guard against reintroducing a blind
  concatenation or redirect-following behavior.
- Rust formatting, dependency and targeted unit tests are independent gates.
- **No real importer end-to-end credentials, Loki data source, or live
  intercepting HTTP server** are qualified here.
- This does not mean all CLI commands and SDKs have completed an egress audit.
- No deployment, release, telemetry enablement or provider services authorized.

Repository remains private with inherited GitHub Actions disabled.

## Verified on macbook (2026-10-24)

- `cargo fmt --manifest-path cli/Cargo.toml --all -- --check`: PASS.
- `cargo metadata --offline --locked --no-deps`: PASS.
- `cargo test --offline --locked --manifest-path cli/Cargo.toml --lib`:
  **257 passed, zero failed**. Targeted intake tests separately passed 3/3.
- Full Flind Python regression `python3 -m unittest discover -s tools/flind
  -p 'test_*.py' -q`: **232 passed, zero failed**.
- `git diff --check`: PASS.
- Note: Rust test binary `--bin posthog-cli` contains zero tests. All substantive
  Rust results above are from `--lib`, not the empty binary test target.
- Compile/test qualified; a genuine Loki import and captured network egress
  trace remain unverified. No release approval.
