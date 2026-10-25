# Wave 109 — Python Capture v1 to Rust Capture v1 source parity

## Qualification added

`tools/flind/test_capture_rust_source_contract_wave109.py` is a Python-standard-library-only regression suite that checks the **actual first-party Django Capture-v1 producer source** against the **exact same Git HEAD's Rust Capture-v1 source**, even if Rust is not present in the local sparse working tree. The Rust files are fetched from checked-out Git objects using a small, explicitly allowlisted set of literal source paths; no GitHub/network access or Rust compiler is needed to run the tests.

The test executes Django Capture's **actual** `_build_v1_headers` function AST with synthetic credentials, then compares generated header names to Rust's actual `REQUIRED_HEADERS` references. It also checks:
- Exact analytics and AI v1 paths in Rust's router constants against Python's internal ingestion default endpoints.
- All mandatory Rust headers exist in the Python producer; Flind's first-party SDK identity is included in both user-agent and SDK info header, with bearer secrets confined to authorization.
- Rust's four `EventResult` enum statuses match exactly Python's known response statuses; Rust serializes a required `result`, wraps UUID-to-outcome mapping under `results`, and includes retry headers when necessary.
- The Rust `Batch` payload fields match the dictionary actually constructed by Python's `prepare_capture_internal_batch` function.
- The Rust `Event` fields match the Python event dictionary, including optional `session_id`, `window_id` and `options`.
- Option keys accepted by Rust match Python's typed option normalizer mapping.
- Distinct analytics and AI routers remain present, and Wave106's fail-closed malformed acknowledgement check has not regressed.

## Evidence — October 26, 2026

Running from the private Git repository at `main` revision `69e320aa594629a132bfab22783d8ad4bea645a2`:

```sh
python3 -m unittest -v tools.flind.test_capture_rust_source_contract_wave109
```

**12/12 PASS**, exit 0; Python compilation and Git diff whitespace checks PASS. Standard-library only (no need to install Django, run Kafka/Redis/PostgreSQL/ClickHouse, or download model weights).

## Real Rust build blocker — documented rather than bypassed

`cargo metadata --offline --locked --format-version 1` was run in an older full-source Rust checkout. It returned **exit 101**, because Cargo's workspace resolution requires a Git dependency `js-source-scopes` at revision `abea51a0e74840a8d1ec96a61ff36b488994f68c` which is **not in the offline cache**. That Git dependency belongs to the workspace; this does **not** prove the Capture service itself would fail once correctly bootstrapped. No online dependency fetch or Rust build was completed in this wave; real capture-rs startup, Kafka publishing, real ClickHouse ingestion and application dashboard are **unqualified**.

The earlier fully locked Python 3.14.7 Django test virtualenv under `/tmp/flind-wave63-runtime` was no longer available in this run; there is a separate older `/tmp/flind-runtime-3147` environment but it lacks several project dependencies. Therefore **no new original Django suite or production DB tests are claimed here**. This source-only guard provides durable coverage without consuming scarce disk, but it does not substitute for native integration.

## Project release boundary

Full SDK→native Rust Capture→Kafka→ClickHouse→authenticated query API→Dashboard, product custom users/tenants, OAuth/PKCE, browser/desktop E2E, production builds and whole-source/binary branding remain open in Issue #82. All release flags must remain false. No public release, paid cloud resource, user data, GitHub Actions enablement or removal of donor licensing.
