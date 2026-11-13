# Flind CLI native telemetry: fail-closed while ownership is unqualified

Status: **Rust format, Python source regression and all-targets Cargo
compilation/test passed locally on WSL Ubuntu (2026-11-13).** This is
native Linux-source qualification, not production, Windows installer,
macOS signing or real DNS/HTTP egress certification.

## Risk discovered

The inherited Rust CLI validates explicitly configured API hosts and
rejects the original vendor's cloud domain. However, this does **not**
protect separate analytics and exception-reporting paths that call
`posthog_rs::capture` or `posthog_rs::capture_exception_with` in:

- `cli/src/invocation_context.rs` (command usage, events and the
  `api` subcommand without an invocation context)
- `cli/src/error.rs` (structured error reporting).

Those reporters are not authenticated by the chosen Flind instance.
Sending them to a library default or external provider would disclose
command metadata, invocation identifiers and possibly project details.

## Scope of the repair

A native Rust gate named `external_telemetry_allowed()` deliberately
returns **false without an environment override** until the project
has an independently owned, reviewed analytics collector.

Every existing native Rust `posthog_rs` dispatch path returns before
calling the library. The no-context API proxy usage hook returns a
joinable no-op thread so its public signature and caller behavior stay
intact. Ordinary error messages still reach local stderr, but the
Flind CLI does **not** submit structured exceptions through that
inherited Rust telemetry library. No CLI data or credentials are
uploaded as part of the tests.

The original API-host validation and allowed explicit local/self-hosted
HTTPS API routes remain intact. The Rust diagnostic gate is **not** a
substitute for validating the destination, tenant and file upload
permissions of an actual source-map or native debug-symbol upload.

## Verification

- `python3 -m unittest tools.flind.test_cli_no_unqualified_telemetry -v`
  checks the disabled constant-like function, placement of the guards
  before all three direct Rust reporter calls, and absence of new
  direct `posthog_rs::capture` calls in other Rust files.
- `cargo fmt --manifest-path cli/Cargo.toml --all -- --check`
  checks formatting.
- Local WSL Rust tests used `cargo test --locked --offline --all-targets
  -- --test-threads=2` with isolated `CARGO_TARGET_DIR`, 2 compile
  jobs and incremental builds disabled. **357 tests passed, 0 failed**:
  272 library, 1 API proxy, 13 debug symbols, 13 Git, 29 module,
  29 sourcemap; binary and example targets contained no tests.
- The first sparse-checkout run lacked tracked Cymbal fixture files,
  causing eight unrelated debug-symbol tests to fail. A second run
  needed original Git-byte source-map fixtures because Windows had
  converted expected LF to CRLF. Both were diagnosed rather than
  hidden: source fixture paths were sparsely added, expected test
  bytes restored from Git for verification, and the **final full test
  run passed**. No fixture changes belong in this PR.

## Explicitly NOT qualified

The `api` subcommand can launch a separately generated JavaScript
bundle through `cli/src/api_proxy.rs`. **This repair does not assert
the embedded Node bundle has zero external telemetry or any hidden
network fetches.** That independently bundled JavaScript program,
install/update logic and the CLI's own source-map/dSYM upload
destination require separate interception/network negative controls.

The CLI remains a staged inherited compatibility binary, not a
published independent Flind installer. All required third-party
copyright/NOTICE provenance stays intact. No public tag, binary,
installation script, SDK, application deployment or release without
founder's explicit `GREEN LIGHT FLIND`.
