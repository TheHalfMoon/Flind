# Flind CLI API proxy host preflight and inherited-host refusal

Status: **native WSL Cargo all-targets tests passed locally (363/363),
Python static contracts passed (13/13), and Rustfmt passed on 2026-11-13**.
GitHub exact-head CI and final security review are separate prerequisites.

## Previously uncovered route

`cli/src/utils/auth.rs` rejects donor domains and insecure public
HTTP for the authenticated Rust API client. Yet `posthog-cli api`
delegates to a separately built Node bundle. It sometimes skips
`init_context` for explicit environment credentials or metadata
operations. Its direct `api_proxy::run` path previously forwarded
`--host`, `POSTHOG_HOST` and `POSTHOG_CLI_HOST` without a new host
validator call, potentially allowing an inherited provider endpoint
to reach the Node child with tokens.

The original CLI vendor analytics env variables had already been
scrubbed separately. This is a different API-routing boundary.

## Fail-closed behavior

Before reading/materializing the Node bundle and before starting Node:

- Validate **all** possible host values: CLI `--host`, the two
  inherited compatibility environment aliases and the saved
  InvocationContext host. The existing Flind host validator rejects
  `posthog.com` and subdomains, credential-bearing URLs, paths,
  query parameters, public plain HTTP, invalid protocols or malformed
  values. Explicit local loopback HTTP and operator-selected HTTPS
  origins remain supported.
- Reject any **conflicting origin values**, even if individually
  valid; users must clear contradictory aliases before proceeding.
- With no approved host, fail closed. Even metadata commands require
  an explicit host until the separate Node bundle passes runtime
  no-egress review; top-level help remains available without running
  Node.
- Clear inherited `POSTHOG_HOST` from the Node process and inject
  **one normalized validated `POSTHOG_CLI_HOST`**. This removes
  accidental routing ambiguity when the Node bundle chooses between
  aliases. Original user API credentials and argument forwarding
  remain supported once the host is valid.

Errors describe the **source** of a bad host, not its value, to avoid
logging credentials embedded in a malformed URL.

## Evidence and limits

Pure Rust unit tests verify negative/positive host resolutions and
child environment normalization. Binary integration tests exercise
the standalone process and verify that the Node script does **not**
execute when passed a donor host, a missing host, or conflicting
aliases. An existing positive subprocess argument forwarding test
now sets an explicit local loopback host.

`python3 -m unittest tools.flind.test_cli_api_proxy_host_preflight -v`
provides a quick source regression, and `cargo fmt --check`
is independent of registry downloads.

The complete WSL run used the pinned `cli/Cargo.lock`, cached offline
Cargo dependencies, a dedicated temporary build directory, and
`cargo test --locked --offline --all-targets -- --test-threads=2`.
**363/363 tests passed** (275 library + 4 API proxy process tests +
13 native debug symbols + 13 Git + 29 module + 29 sourcemap; binary and
example targets contain no tests). The sparse checkout required the
tracked `rust/cymbal/tests/static` ELF/Mach-O fixtures, and the Windows
checkout's CRLF-normalized sourcemap expected fixtures were restored
from Git byte-for-byte *only in the temporary test workspace*. Do not
commit modified test fixtures; preserve original checksums.

This still **does not** prove the Node bundle obeys the selected host
for every route. It may parse its own config files or contain
hardcoded network destinations. A network-namespace egress audit of
the separately generated Node bundle is still required. Do not
claim that this fixes all telemetry, installer/update channels,
upload permissions, or a production cross-tenant security review.

No public tag, binary, package, installer or hosted deployment
without founder's explicit `GREEN LIGHT FLIND`. Preserve required
third-party source licenses and original copyright notices.
