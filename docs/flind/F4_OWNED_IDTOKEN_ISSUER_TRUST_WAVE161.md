# Wave 161 — Trust only Flind-owned ID-token issuers and JWKS

## Security changes

Before this wave, reissued ID tokens used inherited regional constants for JWKS retrieval and determined the region from the unverified token's legacy issuer. A valid signature on the wrong issuer could pass the old signature-only verification path. Additionally, if OIDC_SIGNING_KEY was missing, successful token responses could pass an unverified regional id_token to clients.

- `reissueIdToken` now requires validated `FLIND_OAUTH_US_ORIGIN` and `FLIND_OAUTH_EU_ORIGIN` before key fetch, and uses the selected Flind-owned origin for both the JWKS URL and `jwtVerify(..., { issuer, algorithms: ['RS256'] })`.
- The regional JWKS cache is keyed by the region **and** normalized owned origin, preventing a long-lived Worker from reusing old keys when backend ownership changes.
- `reissueIdTokenInResponse` selects only among the configured Flind issuer origins, then still verifies signature and issuer. Unrecognized issuers cause an error without returning the unverified token.
- A successful regional token response containing `id_token` now fails closed with `server_error`/no-store when the proxy signing key or owned regional trust is absent. Responses with no `id_token` retain the preexisting behavior.
- Tests migrated positive signed JWT fixtures from inherited hosts to synthetic Flind-owned issuers; deliberate inherited-origin denial tests remain unchanged.
- Added regressions for missing owner configuration (no JWKS network), validly signed JWT with an incorrect issuer, JWKS cache isolation across owner changes, and missing signing key denial.

## Actual verification — 2026-10-27

Fetched the exact PR branch from the private GitHub repository and copied the four changed files via Git object reads into the already prepared isolated source test suite on the authorized Mac. Used the free existing standalone runner with actual OAuth handler source and fake HTTP/KV:

```sh
cd /private/tmp/flind-wave160-oauth-suite/services/oauth-proxy
./node_modules/.bin/vitest run --config vitest.config.mts
./node_modules/.bin/tsc --noEmit --project tsconfig.json
```

**Vitest: 13/13 files, 124/124 tests passed, exit 0. TypeScript: exit 0, zero diagnostics.** This qualification used synthetic keys, mock regional responses and a local no-cost runner; it did not contact or provision a real identity provider, production issuer, Cloudflare deployment, secrets, or user data.

## Remaining NO-GO

The global Worker entry gate stays closed. Real Flind-owned backend issuer/JWKS provisioning, actual OAuth/OIDC + PKCE browser/worker/backend integration, token audience binding checks, Django migrations, SDK→Kafka→ClickHouse→API→Dashboard, tenant isolation, product builds and real cross-component E2E remain unqualified (#5 and #82). The inherited constants module is retained behind the admission guard until its final consumers are migrated and checked. Keep repository private, inherited GitHub Actions disabled, no publishing/deployment/paid services, preserve mandatory third-party notices.
