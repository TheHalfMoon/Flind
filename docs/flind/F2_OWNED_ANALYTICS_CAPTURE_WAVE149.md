# Wave 149 — Remove embedded external analytics capture credentials and hosts

## Critical first-party privacy/correctness gap

The source of `posthog/ph_client.py` still embedded upstream public analytics project tokens and both upstream US/EU ingestion hosts. Public project tokens are **not secret authentication credentials**, but they select external projects and can transmit Flind event metadata, prompts and usage data to infrastructure outside this fork. Client constructors and background flush callbacks were reachable from many product paths.

This wave removes the upstream tokens and destinations entirely from this module and leaves **all four related capture values empty by default**:

- `FLIND_CAPTURE_US_API_KEY`
- `FLIND_CAPTURE_US_HOST`
- `FLIND_CAPTURE_EU_API_KEY`
- `FLIND_CAPTURE_EU_HOST`

These must refer to analytics projects/endpoints that the Flind operator actually controls. Do not set vendor-controlled US/EU values.

## Production behavior

- `get_client()` now returns `None` **before constructing a telemetry SDK client** unless both the regional project token and endpoint are configured and the URL is a valid HTTPS origin (or local HTTP loopback). HTTPS URLs with credentials/paths/query strings are rejected; original `posthog.com` and `posthog.io` hosts and subdomains are explicitly disallowed even if someone configures them. This is an input format/origin safety check; it cannot independently establish domain ownership, which the operator must verify.
- Scoped capture now tolerates no client and does not attempt `shutdown()` on `None`. Background capture no longer registers a nonexistent `atexit` flush callback with no configured SDK.
- The feature-flag synchronization command now refuses missing capture configuration **before HTTP**. It no longer uses the old cloud flags endpoint or prepopulates an unrelated customer's/project's fixed group IDs; it uses only the explicitly configured owner-scoped US origin and supplied groups.
- Desktop feedback media lookup refuses unconfigured regional tokens **before a database query**. The feedback event path already guards a missing SDK client.
- Streamlit sandbox OTEL export refuses unconfigured or blocked hosted capture endpoints rather than forming a broken/unowned logs URL.
- AI-observability usage report refuses unconfigured hosted analytics before constructing the SDK client or performing internal reporting-team lookup. When enabled, the client receives the explicitly configured host, rather than a library upstream default.

Existing Python import names and API protocols remain unchanged for compatibility pending full Flind migration; the active first-party branding contract remains `docs/flind/IDENTITY_CONTRACT.md`.

## Actual executed checks on Mac (2026-10-26)

Fetched **exact PR branch** source into an independent, no-network test fixture and ran `tools/flind/test_owned_analytics_capture_wave149.py` under the frozen Python 3.14.7 / 451-package environment.

**11/11 PASS, exit 0.** The test executes production source assignment ASTs, host validator, `get_client()`, scoped and background capture, the feature-flags command, desktop-media admission, Streamlit OTEL configuration, and usage SDK constructor. Stub HTTP and analytics SDK calls assert no outbound side effects without valid owner configuration. It also verifies a positive Flind-owned test host is actually forwarded to a fake SDK, and verifies missing configuration cannot register an `atexit` flush.

A separate check parsed all five modified Python files successfully and inspected the actual installed `posthoganalytics.client.Client` constructor: its `host` parameter is available. The positive SDK test uses a fake client so **no real analytics events or HTTP requests** were sent.

## Limits

The original full Django/ClickHouse/Celery, Desktop, and Streamlit integration test suites remain **unqualified**, because the Mac's sparse/partial Git checkout does not yet boot the full Django application. This behavior intentionally disables optional first-party internal capture and some dependent workflows until Flind-owned projects/hosts are explicitly configured; do not treat that as proof all dependent workflows function without configuration.

This does not remove every legacy analytics SDK import/env/protocol or external destination elsewhere in the monorepo; inventory and migrate each consumer under issue #5. Django database migrations, real Node/Rust→Kafka/ClickHouse capture, authenticated tenant-filtered API/Dashboard, OAuth regional ownership/PKCE and browser E2E remain issue #82. Release NO-GO; private GitHub repo, inherited Actions disabled, no deployment/publication/paid resources, preserve mandatory third-party attribution.
