# Wave 153 — Flind-only regional OAuth client registration

## Legacy production route removed from this handler

The OAuth `/oauth/register/` handler previously posted new client registration metadata and original callback URLs to the upstream project's hardcoded US and EU origins, then persisted the returned regional client IDs in Cloudflare KV. An independently rebranded Flind worker must not register application credentials or callback URLs at an unrelated OAuth authority.

Wave151 already blocks public OAuth ingress until **all** routes are first-party. This wave makes the **production registration handler itself** first-party, with a separate early deny before any outbound fetch.

## Implementation

- `flind-oauth-admission.ts` exposes `flindOAuthOwnedRegionPair(env)`, which atomically validates that both `FLIND_OAUTH_US_ORIGIN` and `FLIND_OAUTH_EU_ORIGIN` are safe, separate first-party origins. Existing `flindOAuthRuntimeReady()` consumes the same validation and **still denies public OAuth** until actual shared handler destinations are all migrated.
- `handlers/register.ts` now takes the Worker env as its third argument. If no safe pair exists, it returns JSON `temporarily_unavailable` **HTTP 503, Cache-Control: no-store**, without reading the registration body, making outbound requests or modifying KV.
- Valid registered-client requests now post only to `${regions.us}/oauth/register/` and `${regions.eu}/oauth/register/`, never the inherited regional constants.
- Existing two-region semantics remain: both registrations must succeed before a client mapping is written; the proxy callback is added to each region's registration metadata, but the original client callback list is preserved in the stored mapping.
- Original `tests/register.test.ts` now uses first-party synthetic domains, supplies env arguments, and tests early denial for absent, vendor and same-region origins.

## Executed source-owned evidence (2026-10-26)

`tools/flind/test_owned_oauth_dual_registration_wave153.mjs` was executed with **Node 24.15.0** `--experimental-strip-types` against the exact GitHub PR branch. It ran the **actual production** `register.ts`, `kv.ts`, `constants.ts` and `flind-oauth-admission.ts` using temporary relative import rewrites, genuine Request/Response objects, fake fetch endpoints and an in-memory KV recorder.

**6 groups PASS, process exit 0**:
1. Missing, inherited-vendor, invalid HTTP or same-region configuration: 503 **before any HTTP/KV**.
2. Two configured first-party Flind regions: both correct outgoing registration endpoints, proxy callback added to the registration, and one KV mapping with both real synthetic regional IDs and original callback.
3. One regional registration failure: no KV client mapping.
4. Both regional registrations fail: no KV client mapping.
5. Current Worker **still refuses all live OAuth** until token, authorize, JWKS, metadata and issuer ownership are aligned.
6. Original Vitest registration tests updated to the first-party env signature and negative route regressions.

The original complete Vitest/Cloudflare Worker suite was **updated but not run**; JavaScript monorepo dependencies are not fully qualified on the constrained Mac. No real OAuth provider, KV, network, credentials or paid service was touched.

## Explicit release limitation

This is a tested **functional step toward first-party Flind OAuth**, not deployment authorization. Public ingress Wave151 remains fail-closed. The regional authorization redirect, code/token exchange, introspection, userinfo, JWKS and OIDC ID-token issuer rewriting remain to be migrated and tested together, plus all Django app, frontend, SDK and data-pipeline E2E. Issue #5 and #82 remain OPEN and release NO-GO.

Private repo, inherited Actions disabled, no publishing/deployment or paid services, preserve copyright/NOTICE obligations.
