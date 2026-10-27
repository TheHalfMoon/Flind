# Wave 163 — OAuth token responses are never publicly cacheable

## Actual issue

The owned-region grant router forwarded upstream responses that could include an inherited `Cache-Control: public`, regional CDN caching directives, `ETag` and `Expires`. This is inappropriate for OAuth token responses containing access/refresh tokens. The ID-token reissue helper also preserved upstream cache headers; and the JWT bearer grant returned the raw upstream response directly. The public Worker ingress remains fail-closed, but direct handler invocation also needs secure cache semantics.

## Fix

- Added `privateTokenResponse` to the token handler for all upstream success/error paths, including JWT bearer and token reissue, and for local malformed/missing-owner denials.
- It sets `Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`; removes `CDN-Cache-Control`, `Cloudflare-CDN-Cache-Control`, `Surrogate-Control`, `ETag`, and `Last-Modified`.
- It constructs a new Response preserving body stream/status/status text/content-type without changing token bytes.
- Adds four regression cases: refresh success, regional grant error, JWT bearer success under intentionally public regional caching headers, plus missing-owner/malformed error denial.

## Real execution — 2026-10-27

Retrieved exact branch files from the private GitHub branch into the already prepared, isolated, free Mac Node OAuth runner. Actual original OAuth service tests with mocked regional fetch/KV, and strict TypeScript checker:

```sh
cd /private/tmp/flind-wave160-oauth-suite/services/oauth-proxy
./node_modules/.bin/vitest run --config vitest.config.mts
./node_modules/.bin/tsc --noEmit --project tsconfig.json
```

**14/14 original Vitest files PASS, 130/130 tests PASS, exit 0. `tsc --noEmit` PASS, exit 0 and zero diagnostics.** The test suite uses synthetic token strings, mocked regional HTTP and KV, not real accounts or production service.

## Ongoing NO-GO

Source-level OAuth security checks are not real PKCE OIDC login with an owned regional issuer, signing key, redirect clients, issuer/JWKS provisioning, or Django/ingestion/dashboard E2E. The top-level Worker admission gate remains intentionally disabled. Full issue #82 integration gates and issue #5 identity gates remain open. Keep repository private and inherited CI disabled, no deployment/publication/paid services; preserve mandatory third-party legal notices.
