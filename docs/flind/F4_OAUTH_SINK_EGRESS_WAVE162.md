# Wave 162 — OAuth transport sinks fail closed on unowned destinations

## Fixed behavior

The OAuth transport shared helpers still contained two unused compatibility exports that implicitly selected inherited vendor regional hosts, and the body-rewriting `proxyPostWithClientId` still fell back to inherited hosts when a caller omitted `ownedOrigins`. Even though the public Worker ingress was gated, these helper functions remained an avoidable direct-call egress risk.

- Deleted legacy implicit-origin `proxyToRegion` and `tryBothRegions` exports (no imports in current OAuth handlers/tests).
- Removed inherited regional host constants from the active proxy transport module.
- Added `checkedOrigins`, which validates both supplied US/EU origins through the shared `flindOAuthOwnedRegionPair` security policy at the actual transport sink.
- `proxyToRegionAtOrigins`, `proxyPostWithClientId` and `tryBothRegionsAtOrigins` now deny missing/vendor/invalid destinations with HTTP 503/no-store before `fetch` and, for body rewriting/fallback, before reading the request body.
- Retained US→EU fallback, client ID rewriting, response selection and proxying only for explicitly validated regional Flind endpoints.
- Added two real transport-source regressions asserting early no-fetch refusal and expected first-party URL list/client-id rewrite for direct, rewritten and fallback requests.

## Local verification — 2026-10-27

Fetched the exact private GitHub branch and copied its modified source and new test file from Git blobs to an existing isolated free Mac OAuth runner. No changes to the stale main checkout, cloud access, user data, deployment, or paid dependencies.

```sh
cd /private/tmp/flind-wave160-oauth-suite/services/oauth-proxy
./node_modules/.bin/vitest run --config vitest.config.mts
./node_modules/.bin/tsc --noEmit --project tsconfig.json
```

**Original OAuth Vitest suite: 14/14 files PASS, 126/126 tests PASS, exit 0. TypeScript: PASS, exit 0.** Uses synthetic regional origins, mocked fetch/KV, and actual application source. This does not constitute live OAuth or production E2E testing.

## Remaining release gates

The top-level OAuth Worker admission check still deliberately blocks public traffic; do **not** reinterpret this fix as authorization to enable it. The separate legacy constants retained for the explicit fail-closed ingress guard must not be removed until real Flind issuers/JWKS, PKCE and authenticated browser/backend flows have been qualified. Full Django migrations, SDK ingestion through Kafka/ClickHouse into tenant-isolated API/Dashboard, UI E2E, packaging identity #5 and release qualification #82 remain NO-GO.

Repository stays private, inherited Actions disabled, no publishing, deployment or paid services. Preserve legally required third-party notices.
