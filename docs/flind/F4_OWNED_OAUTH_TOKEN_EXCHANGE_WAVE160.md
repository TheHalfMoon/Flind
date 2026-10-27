# Wave 160 — OAuth grants route only to owned Flind regions

## Security gap closed

The original `handleToken()` delegated authorization-code, refresh-token, and JWT bearer-grant requests to a regional routing helper with hardcoded inherited upstream origins. Even after prior migrations for registration, authorization, introspection, revoke, UserInfo and JWKS, direct token handler calls could still emit an OAuth code or refresh token to unowned regional infrastructure.

## Production changes

- `handleToken(request,kv,env)` now requires `FlindOAuthRegionEnv & SigningKeyEnv` and verifies both configured regional origins through `flindOAuthOwnedRegionPair(env)` **before reading the grant body or hitting KV/HTTP**. Missing, original-vendor, duplicate region or unsafe hosts fail closed with HTTP 503/no-store.
- All JWT-bearer grant and unknown-region refresh fallbacks now use `tryBothRegionsAtOrigins(..., regions)` with the validated Flind US/EU pair.
- Registered client grant exchanges pass `regions` through `proxyWithMapping()` and the `proxyPostWithClientId()` client-id/client-secret rewrite helper. Original per-region client mapping, redirect callback rewrite, audience lookup, and refresh fallback selection semantics are preserved.
- **Authorization code isolation fix:** when a selected region exists but its client mapping is absent from KV, the code is now sent **only to the selected region** using `proxyToRegionAtOrigins`, never tried against another region. Missing selected region still fails without forwarding the code.
- Existing `token.test.ts` fixtures were updated to use owned synthetic regions in the handler call and first-party OAuth callback/redirect URLs. The one legacy synthetic signed regional JWT issuer remains for the upcoming **issuer/JWKS trust migration**, and is not evidence of qualified first-party OIDC authentication.
- Two additional regressions prove missing owner configuration blocks network and KV, and an orphan code selected for EU is never forwarded to US.

## Actual verification (2026-10-27, Mac)

Constructed a separate standalone OAuth source checkout from the private GitHub branch and cached Git blobs. Restored missing source files through GitHub, left the user's original checkout untouched, installed only free npm modules in a scratch test runner under `/tmp`, no full monorepo install.

The first run found seven outdated fixture regex expectations referencing the old regional host names (six failures; the seventh assertion was not exercised on a failing branch). Updated those **test expectations**, not production routing.

**Full original OAuth Vitest suite: 13/13 files PASS, 121/121 tests PASS, exit 0**. **TypeScript `tsc --noEmit --project tsconfig.json`: PASS, exit 0, no diagnostics**. Tests exercised actual production handlers with fake HTTP responses and fake KV; no real regional endpoint, token, customer data, payment, cloud deployment, or publication occurred.

## Remaining gates

The ID-token reissue verifier in `idtoken.ts` and `token-response.ts` still derives regional issuer/JWKS trust from inherited constant origins; real Flind regional issuer verification and active OIDC signing-key provisioning remain to be migrated and tested. The Wave151 public Worker ingress gate remains deliberately closed until **all** inherited token/JWT/issuer dependencies and genuine OIDC/PKCE end-to-end have passed. Full Django migrations, SDK→Kafka/ClickHouse→tenant-authenticated API/Dashboard, browser/desktop and private-release qualification still block #82; identity/protocol cleanup #5 remains ongoing. Preserve required third-party license notices. Repo remains private, inherited Actions disabled; no deploy/publication/paid services.
