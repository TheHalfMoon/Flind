# Wave 151 — Fail-closed Flind OAuth regional ownership boundary

## Why this must exist before any OAuth release

The inherited OAuth worker still carries old regional hosts in its `constants.ts` and uses them from multiple security-sensitive paths: discovery metadata, client registration, authorization redirects, code/token exchange, introspection, userinfo and JWKS. These endpoints process **authorization codes, user identity assertions, client credentials and access tokens**. Rebranding the worker or defining new Flind environment variables does not by itself change those outgoing destinations.

Until Flind controls both actual upstream OAuth regions, **none of these routes may forward to the inherited vendor**.

## Production implementation

- `services/oauth-proxy/src/lib/flind-oauth-admission.ts` validates configured `FLIND_OAUTH_US_ORIGIN` and `FLIND_OAUTH_EU_ORIGIN`. Both must be distinct, valid HTTPS origins (HTTP permitted only for loopback-only development), without URL path, query, embedded credentials or fragment. Old vendor domains and deceptively embedded vendor names are rejected.
- Critically, configuration alone does **not** enable OAuth. The **actual compiled handler destinations** `REGION_BASE_URLS` must exactly match both configured owner-controlled origins. Current inherited source constants do not, so **admission is deliberately disabled even if Flind URLs are supplied**.
- `src/index.ts` applies the gate after existing URL/method/duplicate-param validation but **before** any external OAuth handler can access KV, fetch metadata, forward secrets or redirect to a regional server.
- Unqualified OAuth endpoints respond `503` with a generic JSON `temporarily_unavailable` and `Cache-Control: no-store`. Static font assets and harmless `/` landing are unaffected. Unknown paths still return 404 and malformed duplicate auth params still fail validation (400).
- Original `services/oauth-proxy/tests/router.test.ts` now includes blocked-route/zero-fetch/zero-KV assertions and first-party configuration refusing the inherited compiled handlers. Its two existing handler-exception tests explicitly mock the gate **only inside tests** to continue exercising async/sync exception handling; production has no gate bypass.

**Do not set a boolean env toggle to bypass the gate.** The only acceptable completion is migrating every actual backend route, metadata rewrite, regional cookie routing, issuer/JWKS, registration and token exchange to Flind-owned instances while preserving PKCE/state and auth contracts.

## Executed evidence (Mac, Node 24.15.0, 2026-10-26)

From the exact GitHub branch, ran `tools/flind/test_oauth_regional_admission_wave151.mjs` under Node24 `--experimental-strip-types`, importing and executing the **actual TypeScript helper source** from a clean disposable temporary file.

**8 assertion groups PASS, exit 0**:
- No region configuration denies.
- Owned Flind env values cannot override the current inherited actual backend routing.
- Explicit vendor region origins remain rejected.
- When an eventual implementation truly uses matching two distinct owner origins, the helper can allow the safe configuration.
- Blocks lookalike vendor labels, non-loopback HTTP, credentials, URL paths/queries and same-region URL configuration.
- Two distinct loopback test origins accepted.
- Source-level worker route inspection shows gate occurs before handler and returns uncacheable 503.
- Original router tests assert no outbound fetch or KV writes on blocked routes.

The **original Vitest Worker suite was updated but not run** because full monorepo JavaScript tooling and Cloudflare Worker dependencies have not been qualified on the constrained Mac. The standalone Node24 test executes the production gate function, not an entire Worker runtime. No Cloudflare deployment, remote OAuth request, KV mutation, money spent or real user authentication occurred.

## Release boundary

This is an **intentional fail-closed security gate**, **not** an operational Flind OAuth release. It protects the fork while #5 migrates identities and backends, and #82 qualifies full OIDC/PKCE/registration/callback/refresh/revoke/JWKS against first-party Flind environments. OAuth should stay unavailable until those gates pass. Full Django migration, Kafka/ClickHouse ingest, authenticated API/Dashboard and tenant isolation also remain NO-GO under #82.

Repository remains private, inherited Actions disabled, no publishing/deploying, and mandatory third-party legal attribution preserved.
