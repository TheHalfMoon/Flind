# Wave 220 - safe actionable Django registry error diagnostics

## Motivation

A current-main, read-only Django migration registry import on the
isolated Python 3.14.7 Mac runtime returned a generic
"Unhandled first-party registry error" when the cache backend was
missing. That hid the actionable exception class and made it impossible
to distinguish a dependency error from an actual source error.

## Change

The existing first-party offline Django registry probe now reports a
bounded Python exception **class name** for previously unhandled
exceptions. It NEVER includes exception messages, tracebacks, URLs,
tokens, filesystem paths or installed environment values. Non-identifier
or overlong class names still produce the previous generic result.
The existing try/finally resource cleanup and all established error
handling remain in place.

## Verified evidence

- Actual source checkout: private Flind main after Wave 218, commit
  9b777331472c1b343ddd0d1a9b4e5517ded7b315.
- Python 3.14.7 original source regression suites: **22/22 PASS**
  (4 new negative/positive diagnostics, 18 existing sparse registry).
- Python compilation and Git diff whitespace validation: PASS.
- Previous current-main migration import is still BLOCKED by missing
  dependencies, last observed missing package oauth2_provider in
  the isolated scratch runtime. No migration graph or real E2E PASS
  claim follows from this change.
- No database operations, production data, Docker mutations,
  deployment or public release. Host Windows disk and WSL I/O
  remain blockers, see issue #253.

## Release boundary

This is a developer-diagnostics improvement only. Full Django
dependency qualification, original PostgreSQL/ClickHouse migrations,
first-party Rust+Node joined ingestion, tenant/auth, SDK and browser
tests remain outstanding. **Release NO-GO**. Repository PRIVATE,
Actions disabled.