# Wave 159 — First-party JWKS fetch and cache rotation isolation

## Two real auth correctness defects

`services/oauth-proxy/src/handlers/passthrough.ts` previously fetched `/.well-known/jwks.json` through the legacy hardcoded regional proxy. Even after the owner-configured discovery, authorize, registration, UserInfo, introspection and revoke migrations, direct JWKS handler invocations could reach an unrelated regional key authority.

In addition, JWKS responses were held in one module-scoped `cachedJwks` entry keyed **only by time**. Changing the active signing PEM after Wave157 or changing the Flind regional owner origins could still serve an old public signing key set for the entire cache TTL in a long-lived isolate.

## Production behavior

- New `proxyToRegionAtOrigins(request, region, path, ownedOrigins)` forwards to **only the explicitly supplied** validated Flind origins. The legacy `proxyToRegion()` remains for not-yet-migrated token/issuer paths behind the Wave151 public-ingress gate, and is no longer invoked by JWKS.
- `handleJwks(request, kv, env)` now requires `FlindOAuthRegionEnv & SigningKeyEnv`; `flindOAuthOwnedRegionPair(env)` is validated **before any network or JWKS cache access**. Missing/vendor/same-region destinations return `503` and `Cache-Control: no-store`.
- The cache identity is now `JSON.stringify({us, eu, kids})`, with validated regional owner URLs and **public** proxy `kid`s from `proxyJwks(env)`. No private signing PEM enters the cache identity.
- A different backend authority or active/inactive PEM reconfiguration changes the public key set identity, forcing a fresh regional fetch and refreshed combined JWKS instead of reusing old cached keys.
- Existing 'partial JWKS must not cache' behavior and the proxy-key-only response on a simulated regional outage remain intact. A normal unchanged key set can still be cached for its configured 600-second TTL.
- Updated original `idtoken.test.ts` direct JWKS cases to provide first-party synthetic owned origins and expected region URLs, and added `owned-jwks.test.ts` with absent/vendor/same-region no-fetch regressions, origin cache isolation and real generated RSA private-key rotation.

## Executed qualification, 2026-10-26

The exact private GitHub Wave159 branch files were placed into an isolated Node24/Vitest4.1 + TypeScript5.9 test workspace on the connected Mac, without touching the user's Flind checkout. No provider/Cloudflare connection was opened.

The initial run revealed 2 old `idtoken.test.ts` direct JWKS fixtures with missing new regional owner env; 117/119 passed. Updated those fixtures, preserving their signing and public-regional-key assertions.

**Final full original OAuth Vitest: 13/13 files PASS, 119/119 tests PASS, process exit 0 (2.67s)**. **Actual TypeScript `tsc --noEmit --project tsconfig.json`: PASS exit 0, no diagnostics**. The new cache tests explicitly mock an upstream that returns two regional public keys, change the owner US host without waiting for cache expiration, and rotate a freshly generated PKCS#8 RSA signing PEM to prove both trigger cache refresh. No production secrets or paid services.

## Still not a full OAuth or product release

`idtoken.ts` upstream JWT signature verification and token reissuance still use inherited regional constants; token exchange and its fallback path also require owner-only migration with strict OIDC issuer/PKCE/audience/key verification. Wave151 global Worker ingress remains deliberately **NO-GO** until *all* live regional endpoints are migrated and independently qualified. Real Flind server OIDC, Django migrations/registry, data ingest SDK→Kafka→ClickHouse→tenant-filtered API/Dashboard, and UI/browser E2E remain tracked in issue #82. First-party identity/protocol compatibility remains #5.

GitHub repository private, inherited Actions disabled, no publication/deploy/paid services, legally required attribution preserved.
