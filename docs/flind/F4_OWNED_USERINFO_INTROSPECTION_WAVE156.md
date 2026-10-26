# Wave 156 — First-party regional OAuth introspection and UserInfo

## Before

The public OAuth Worker ingress was already locked down by the Wave151 fail-closed gate. However, even direct source-level `handleIntrospect` and `handleUserInfo` calls still selected hardcoded upstream US/EU destinations, which is unacceptable before Flind's first-party OIDC ownership is complete. An incomplete migration that changed just the client-facing discovery/authorization routes would not protect bearer token or introspection queries.

## Production changes

- `handleIntrospect(request, kv, env)` and `handleUserInfo(request, kv, env)` now call `flindOAuthOwnedRegionPair(env)` **before reading/forwarding token-bearing request data**. Missing, original-host, duplicate/same-region or non-loopback HTTP origins return `503` with `Cache-Control: no-store`, **before fetch**.
- Both use only `FLIND_OAUTH_US_ORIGIN` and `FLIND_OAUTH_EU_ORIGIN` from the Worker's owned, validated environment. The introspection handler uses US first, then EU if the US response doesn't report an active token.
- New `tryBothRegionsAtOrigins(request,path,origins)` permits explicitly supplied owner-controlled destinations. The original `tryBothRegions()` remains for legacy **token and revoke** callsites, deliberately still **blocked at public ingress** pending those routes' full migration. New UserInfo never invokes that old implicit-region API.
- Both token-bearing response handlers force `Cache-Control: no-store` irrespective of upstream response headers, including an EU introspection response. A new `privateOAuthResponse()` preserves the response body/status, removes a stale content length, and overwrites inherited cache policy.
- Added `services/oauth-proxy/tests/owned-passthrough.test.ts`: negative origin admission for both paths, correct owned US/EU targeting, introspection active vs inactive routing, token forwarding, and no-store even when a test upstream incorrectly responds `public, max-age=3600`.
- **Public OAuth stays disabled**: `flindOAuthRuntimeReady(env, REGION_BASE_URLS)` still checks the old constant destinations used by token/JWKS routes and refuses ingress with 503. This is a staged backend migration, not a release.

## Executed evidence (2026-10-26)

On a connected 8 GiB Mac, built an isolated service runner in `/tmp`, using **free npm dependencies** Vitest4.1, Vite TS-config paths, JOSE6.2, TypeScript5.9, and Cloudflare worker types. No full monorepo install or user checkout modifications.

A stale local `origin/main` view was detected and rejected as an inadequate source of truth; the fixture was corrected against the exact private GitHub Wave156 branch commit. Of 34 tracked service files, 24 were read directly from the corresponding Git objects and 10 were restored from GitHub source, while deleted `fonts.ts` and `fonts.test.ts` were removed from the scratch copy. Testing only proceeded after matching the actual branch tree.

**Original full service Vitest**: **10/10 test files PASS, 108/108 individual tests PASS, exit code 0** (1.95 sec). **Full TypeScript `tsc --noEmit --project tsconfig.json`: PASS exit 0, zero diagnostics.** No real OAuth backends, external network requests, Cloudflare KV, signing keys or customers used: network responses and KV were local mocks.

## Non-release gates

The remaining token, refresh, revoke, signing/JWKS and issuer pathways still include hardcoded upstream identifiers. Real Flind-owned OIDC/PKCE/token/key rotation E2E remains required before removing the Wave151 Worker gate. Full Django registry/migrations, Kafka/ClickHouse ingestion, tenant-isolated authenticated API/Dashboard and browser/desktop regression also remain unqualified (issue #82). Name/protocol migration #5 remains open.

Repo PRIVATE, inherited Actions disabled, no deploy or public release, no paid resources, legal attribution remains intact.
