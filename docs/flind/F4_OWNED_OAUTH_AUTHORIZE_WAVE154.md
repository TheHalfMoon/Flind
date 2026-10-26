# Wave 154 — Owned Flind OAuth authorization redirects and region picker identity

## Functional first-party redirect migration

The original OAuth authorization handler still called inherited `baseUrlForRegion()`, which returned upstream vendor US/EU origins even if a Flind operator supplied first-party regional endpoints. This route carries OAuth client identifiers, state/nonces, PKCE challenge and authorization redirect URIs, so it must not redirect users to an unowned authorization server.

Wave151's global Worker ingress stays fail-closed until every real route is migrated; Wave154 migrates the **real authorization handler** in preparation for full OIDC/PKCE qualification.

## Production implementation

- `handleAuthorize(request, kv, env)` obtains both regional destinations through `flindOAuthOwnedRegionPair(env)` **before looking up cookies, KV or redirecting**.
- Missing, inherited-vendor, malformed or identical origins return **HTTP 503, no-store**, with no outgoing redirect, KV lookup/write or exposure of authorization parameters.
- Explicit `_region=us/eu` and a unique valid live-region cookie now redirect only to the corresponding **Flind-owned** origin. The internal `_region` routing parameter is never forwarded.
- Existing registered-client mapping and security logic were preserved: regional client ID replacement, registered callback URI validation, proxy callback URL insertion, pending callback nonce and original state storage, and KV region affinity. Unregistered callback URI errors still reject before KV writes.
- The static `region-picker.html` no longer displays the donor's logo, company, regional links or footer. It uses a first-party **Flind** wordmark/text, system fonts, generic US/EU region labels and no invented Flind production domain. Historical font/protocol assets under source control may remain pending inventory and legal review.
- Existing Vitest `authorize.test.ts` cases now use synthetic first-party Flind hosts and a configured third handler argument, plus missing/unowned region no-KV/no-redirect regression cases.

## Executed verification (2026-10-26)

Node 24.15.0 ran `tools/flind/test_owned_oauth_authorize_wave154.mjs`, fetching the exact GitHub branch and loading original TypeScript `authorize.ts`, `kv.ts`, `validation.ts`, `constants.ts` and `flind-oauth-admission.ts`. The static HTML import was replaced with the **exact committed page text**, allowing real handler execution under Node `--experimental-strip-types` without installing all monorepo JS packages. Only the test imports were rewritten to relative ESM paths. Used genuine Request/Response, fake KV and network-denying fetch.

**7 groups PASS, exit 0**:

1. Missing/vendor/same-region origins deny before KV or redirect.
2. Region picker renders Flind first-party identity with no original remote links.
3. US region redirects to owned origin without forwarding internal `_region`.
4. EU client mapping translates client ID, proxy callback URI, and stores nonce.
5. Unregistered callback rejected before KV mutation.
6. The public Worker continues to reject all external OAuth because token/JWKS/issuer routing has not migrated.
7. Original Vitest cases have been adapted to first-party URLs and handler arguments.

These are **actual production handler/unit tests**, not browser/Cloudflare Worker E2E or full original Vitest suite. No remote OAuth server, user token, KV instance or paid service was contacted; the full JS dependency tree remains unqualified on the constrained Mac.

## Remaining release blockers

Do not bypass Wave151. The entire token exchange pipeline, refresh/revoke/introspection/userinfo, JWKS and OIDC issuer rewriting still must be converted to Flind-owned region routing, with real PKCE/state/callback, key-rotation, auth scopes and token-audience E2E. The browser/desktop, Django migrations, SDK→Kafka→ClickHouse→Dashboard and tenant isolation release gates are still unqualified (#82). First-party identity is tracked by #5. This is a no-deploy PRIVATE GitHub project, Actions inherited disabled, no paid services, legal license obligations retained.
