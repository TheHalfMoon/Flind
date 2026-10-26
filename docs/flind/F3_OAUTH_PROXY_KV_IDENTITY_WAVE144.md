# Wave 144 — Flind OAuth worker identity and inherited Cloudflare KV isolation

## Actual unsafe inherited state

`services/oauth-proxy` contains live OAuth, OIDC and region-routing logic that **still directs traffic to** `https://us.posthog.com` and `https://eu.posthog.com`. Its Cloudflare Worker configuration previously included a concrete external KV namespace ID and a generic worker name. Its `/` handler visibly advertised the upstream vendor and upstream documentation URL.

In the private, unpublished Flind fork, this is neither acceptable first-party branding nor a deployable owned authentication stack. **We did not deploy it.**

## Scope of changes in this wave

1. Rename the Wrangler Worker name to `flind-auth-proxy` without inventing a Flind domain.
2. Remove the **inherited production KV namespace ID** from `wrangler.jsonc`. The `AUTH_KV` binding name is retained for local tests; the owner must provision an entirely new, owned namespace before any eventual deployment. An absent deployment ID intentionally blocks reuse of the upstream resource. No identity or endpoint is invented.
3. Return a first-party `Flind OAuth Proxy` response at the HTTP `/` route rather than the upstream vendor/docs URL. Update the existing router test's exact landing-text assertion.
4. Rebrand private `@flind/auth-proxy` package display metadata (description, maintainer and discoverability keywords), preserving version, package name, licenses, dependencies, scripts, and runtime implementation.
5. Add `tools/flind/test_oauth_proxy_identity_wave144.mjs` as a targeted read-only Node24 regression validating these files against the exact GitHub branch.

## Actual executed evidence

Fetched the GitHub branch to the Mac's untouched sparse Flind checkout and ran `node tools/flind/test_oauth_proxy_identity_wave144.mjs` with `FLIND_SOURCE_ROOT` and `FLIND_TEST_REF=FETCH_HEAD`. **PASS exit 0**:
- First-party package metadata now uses Flind, without altering packages.
- Wrangler config parses as JSONC, worker name is Flind and its KV binding has no inherited external namespace ID.
- Worker root response and existing Vitest router assertion both use exact `Flind OAuth Proxy`.
- The test **explicitly identifies** still-hardcoded US/EU upstream OAuth destinations.

## Nonnegotiable blocked migration

This is a **deploy-safety and branding fix**, **NOT a qualified first-party OAuth service**. The existing `src/lib/constants.ts` and handlers still contain the original US/EU regional origins, old regional cookie names, font/asset imports and external OAuth token/JWKS/issuer behavior. Do not add any old KV ID back or deploy with these endpoints. The next functional wave must migrate regional URLs, client ID mapping, callback/PKCE/OIDC issuer and audience, cookie semantics and real first-party origins together. Test registration/authorize/callback/token/revoke/introspection/JWKS end-to-end against isolated Flind-owned servers first.

The full original Vitest suite was **not run** in this wave because native monorepo JavaScript dependencies remain unqualified on the resource-limited Mac. The Node24 check validates the changed source and configuration, not an actual Cloudflare Worker execution.

Issues #5 (first-party identity) and #82 (integrated product/runtime release) remain open, and this service must not be deployed/published. GitHub repository private, inherited Actions disabled, no paid services and mandatory legal attribution preserved.
