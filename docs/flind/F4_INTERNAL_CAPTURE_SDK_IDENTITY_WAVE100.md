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
- **171/171** original Django capture-internal tests PASS in the isolated Python 3.14.7 environment against the patched production Python module and patched original test file, exit code **0**. The subset `TestBuildV1Headers` independently passed **3/3**. Dev-only prerequisites `django-linear-migrations==2.19.0`, `parameterized==0.9.0` and `fakeredis[lua]==2.23.3` were installed in the **temporary runtime only** using free packages; no dependency files or lockfile were modified.
- The runtime was supplied with synthetic/unreachable Django service URLs and no inherited credentials. The temporary test checkout files were restored afterward. A negative-test serialization TypeError was printed during the suite but the final Django summary was `Ran 171 tests ... OK`.
- Real Rust capture HTTP, Kafka consumer and dashboard integration remain **unqualified**; passing the Django suite is not evidence of their functionality.

## Overall release

Full production ingestion SDK → capture-rs → Kafka → ClickHouse → API → dashboard, identity cleanup of the entire source, OAuth and tenant access, full frontend build and Playwright remain unqualified. The separate Wave 100 real isolated PostgreSQL SessionStore test also passed and should be treated as authentication *storage* proof, not proof of real login.

Preserve original third-party authorship/licensing metadata and all legally required notices. No public release, deployment, paid providers or inherited GitHub Actions.
