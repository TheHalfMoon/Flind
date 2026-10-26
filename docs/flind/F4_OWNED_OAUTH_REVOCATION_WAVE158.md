# Wave 158 — Flind-owned OAuth revocation

## Previously inherited token-revocation destination

Even after moving the OAuth discovery, registration, authorize, introspection and UserInfo handlers to owner-configured Flind regional URLs, `handleRevoke()` still called the implicit-origin proxy. Revocation is a bearer-token-bearing endpoint. Its direct handler path could therefore forward a token and `client_id` to the old vendor regional API.

The Wave151 Worker ingress gate remains fail closed for all public OAuth traffic until *every* remaining token/JWKS/issuer route is owned and tested; this wave also makes **the revocation handler itself** safe if invoked directly.

## Actual source changes

- `handleRevoke(request, kv, env)` validates `flindOAuthOwnedRegionPair(env)` before touching KV or the input token. Absent, vendor-host, or duplicate regions return uncacheable HTTP 503 and **do not fetch or read KV**.
- The internal `routeByClientId()` now takes a mandatory validated `OAuthRegionalOrigins` pair.
- For mapped clients, the existing regional ID rewrite uses an explicitly supplied regional base URL through a new optional `ownedOrigins` argument on `proxyPostWithClientId()`. For unknown-region tokens the revocation path uses the already qualified `tryBothRegionsAtOrigins()`.
- The **legacy** implicit-origin `proxyPostWithClientId` call signature remains for the not-yet-migrated token handler and is still unreachable through the public Worker's Wave151 fail-closed gate; removing it requires the staged token/JWKS/OIDC migration and real authentication tests.
- Added `tests/owned-revoke.test.ts` with early denial cases, region-mapped ID rewriting and owner-only two-region fallback.

## Executed qualification

Ran the **entire original OAuth Vitest suite** from an isolated Node24 + Vitest4.1 environment against the private GitHub branch source using mocked HTTP/KV and synthetic client credentials.

**12/12 test files PASS, 116/116 tests PASS, exit 0**. The five new tests cover no-origin/vendor/duplicate fail-closed admission, EU mapping and client ID rewrite, and US→EU owned origin fallback. **Actual `tsc --noEmit --project tsconfig.json` PASS, exit 0, zero diagnostics** (TypeScript5.9.3 and Cloudflare types). Existing OIDC key-rotation, cross-client state, token, metadata and authorization regressions remained green.

No actual token, remote provider, Cloudflare KV, real customer, paid service, deploy or production data touched.

## Still blocked

**This is a qualified unit/integration source migration, not full public OAuth readiness.** Regional token exchange, ID token reissuance, JWKS discovery/verification, issuer identity, PKCE/state, live key rotation and real browser/client sessions still require first-party migration and end-to-end testing. Flind's complete Django migrations, SDK→Kafka→ClickHouse→tenant-isolated API/Dashboard and UI E2E also remain blocked (#82), and identity/protocol inventory remains #5. Repo private, inherited Actions disabled, no publication, no paid resources, required legal attribution preserved.
