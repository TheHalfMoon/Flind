# Wave 148 — Require a first-party offline evaluation destination

## High-impact inherited egress default

`products/posthog_ai/eval_harness/offline_results.py` configured `OfflineEvalSettings.host` and `from_env()` with the upstream US hosted endpoint. Supplying only an offline-evaluation API key could therefore implicitly select an **unowned host** for full evaluation inputs/outputs, traces, scores and experiment data. This was inconsistent with Flind identity and unsafe for a private fork.

`products/posthog_ai/eval_harness/harness/lifecycle.py` likewise assumed that upstream host for application trace matching, even with no owner-controlled internal analytics team.

## Production changes

- Direct `OfflineEvalSettings(...)` construction now defaults to **`http://127.0.0.1:8010`**, a local loopback Flind test destination rather than an external upstream domain. This preserves existing local/unit publishers that explicitly instantiate the class.
- When the offline upload configuration is created **from environment**, an API key without any explicit destination now raises `OfflineUploadError` **before constructing a publisher or making HTTP requests**.
- The new first-party `FLIND_OFFLINE_EVAL_HOST` takes precedence. Explicit `POSTHOG_OFFLINE_EVAL_HOST` remains a transitional compatibility fallback, but there is no implicit upstream URL. Existing actual Pydantic `normalize_host()` still enforces HTTPS or HTTP loopback origin and rejects invalid paths, embedded credentials and non-loopback HTTP.
- The `EvalContext` now links application traces to the configured `settings.FLIND_HOST` **only when** `LLM_ANALYTICS_INTERNAL_TEAM_ID > 0`; otherwise the trace host and project identity are absent. Neither an upstream host nor an upstream team is implicit.
- Updated existing original offline-evaluation tests: upload suites require explicit Flind host, missing host fails closed, first-party host precedence, invalid configuration tests retain a valid explicit host to exercise their intended failure cause.

## Executed proof

On 2026-10-26 fetched the exact GitHub branch source into a disposable, independent Mac fixture. Ran `tools/flind/test_offline_eval_explicit_host_wave148.py` on **pinned CPython 3.14.7 with the actual frozen, 451-package runtime**.

The test compiles and executes the **entire production `OfflineEvalSettings` Pydantic class**, including its real validators and `from_env()`. It rebuilds the model using real Pydantic, no mocking of admission logic or hostname validation. It also executes the real AST expressions of the trace context under configured/unconfigured fake settings.

**7/7 PASS, exit 0**, covering local-only direct default, no key→no upload, key-only→error before upload, explicit Flind host precedence, explicitly configured legacy origin compatibility, invalid host rejection, and trace attribution requiring an owned internal team.

The original full offline-evaluation Django/pytest suite was updated but **not run** because the 8 GiB Mac's partial/sparse first-party source checkout has not qualified full Django app startup. No HTTP provider, database, paid service or actual upload was called in this wave.

## Remaining first-party identity work

Older API env names and canonicalization aliases for the upstream system are still technical compatibility debt under issue #5 and must be removed with qualified SDK/endpoint migrations. This wave eliminates **implicit** upstream outbound evaluation destinations, not all explicit legacy compatibility modes. Real Flind-owned OAuth endpoints, Django migrations, Node/Rust ingestion, tenant-isolated query and Dashboard E2E remain issue #82, release **NO-GO**. Keep repository private, inherited Actions disabled, never publish/deploy without request, do not remove legally required attribution.
