# Wave 100 — Flind v1 internal capture SDK attribution

## Real runtime defect fixed

The first-party Django `posthog/api/capture.py` internal v1 capture client sent the inherited SDK identity `posthog-capture-v1-internal/1.0` as both its `User-Agent` and its `PostHog-Sdk-Info` value. This string is copied into the v1 capture request context and used for event library attribution. It therefore leaked inherited client branding into Flind-generated event metadata.

The SDK attribution **value** is now `flind-capture-v1-internal/1.0`. The first-party name is distinct from the legacy third-party donor identity, and user tokens never enter this value.

## Compatibility boundary

The HTTP **header keys** `PostHog-Sdk-Info`, `PostHog-Attempt`, `PostHog-Request-Id`, and `PostHog-Request-Timestamp` remain unchanged because the existing `rust/capture/src/v1/constants.rs` and v1 request parser explicitly require them. They are wire protocol keys, not user-facing branding, and removing/renaming them on one side alone would break ingestion.

No changes were made to Bearer authorization, retry counters, event JSON serialization, capture endpoint, ClickHouse schema, Kafka consumer or session storage.

## Tests — 25 October 2026

- **5/5** new Python functional tests PASS against the **actual extracted** `_build_v1_headers` function from Flind's source (not a reimplemented mock).
- Validated new first-party SDK attribution, unchanged native Rust capture-v1 header-key contract, token isolation, unique request IDs, retry attempts, and updated assertions in the donor's original capture API tests.
- `py_compile` and `git diff --check` PASS.
- The full `posthog/api/test/test_capture_internal.py` Django suite and real Rust capture HTTP integration were **not** executed in this limited sparse runtime, so end-to-end compatibility is still an open gate.

## Overall release

Full production ingestion SDK → capture-rs → Kafka → ClickHouse → API → dashboard, identity cleanup of the entire source, OAuth and tenant access, full frontend build and Playwright remain unqualified. The separate Wave 100 real isolated PostgreSQL SessionStore test also passed and should be treated as authentication *storage* proof, not proof of real login.

Preserve original third-party authorship/licensing metadata and all legally required notices. No public release, deployment, paid providers or inherited GitHub Actions.
