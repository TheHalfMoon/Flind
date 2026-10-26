# Wave 152 — First functional Flind OAuth backend migration: discovery and auth manifest

## Prior release blocker

Wave151 added a required security boundary that refuses all external OAuth requests until the actual configured regional backends are Flind-owned. At that point, even OAuth discovery, OpenID metadata and `auth.md` still directly fetched `https://us.posthog.com` from the original project's regional constant. Those paths could not safely be enabled.

This wave **rewires the real metadata handlers** without weakening Wave151's public-ingress gate.

## Production implementation

- `services/oauth-proxy/src/lib/flind-oauth-admission.ts` now exposes `flindOAuthDiscoveryOrigin(env)`, using the same origin validation that rejects the upstream project, deceptive lookalike hostnames, non-loopback HTTP and credential-bearing/malformed URLs.
- `services/oauth-proxy/src/handlers/metadata.ts` accepts the Worker-provided `env` and requires a valid explicit `FLIND_OAUTH_US_ORIGIN`. With no valid Flind owner origin, **HTTP 503 before any fetch**.
- OAuth metadata / OIDC configuration / `auth.md` are fetched only from the validated backend origin. The old upstream US constant is absent from this source.
- Returned discovery endpoints are rewritten to the user's requested Flind proxy origin, including nested `agent_auth` links. A URL with a deceptively similar host (`us.flind.example.evil`) is **not** rewritten as a legitimate Flind origin.
- The persisted regional origin field `posthog_base_url` retains the issuer/backend origin until schema compatibility migration, while public endpoint fields are proxied.
- Backend origin participates in discovery/manifest cache keys so changing operators/backends cannot reuse a cached response from another origin.
- Original metadata Vitest cases now use synthetic Flind-owned origins and supply the Worker handler's KV/env signature, with new fail-closed/no-fetch, exact owner-target and lookalike regressions.

## Actual execution evidence (2026-10-26, Mac)

Ran `tools/flind/test_owned_oauth_discovery_wave152.mjs` on Node 24.15.0 with native TypeScript stripping. From the exact GitHub PR branch, the script temporarily assembled the **actual production `metadata.ts` and both dependent source modules** into an isolated ESM fixture, rewriting only `@/lib` imports to relative test-fixture imports. It executed the real handlers and validator against in-memory `fetch` mocks and `Request`/`Response` objects.

**8 groups PASS, exit 0**:
1. Missing Flind region: 503, zero fetches.
2. Upstream vendor region: 503, zero fetches.
3. Owned Flind region: correct request destination and nested public rewrite, preservation of regional identity field, no lookalike rewrite.
4. Cache avoids repeat fetch for the same backend.
5. Cache keyed by backend origin (no cross-owner reuse).
6. OIDC discovery uses the validated Flind region.
7. `auth.md` fetched from Flind and rewrites only the exact legitimate origin.
8. Original Vitest source updated to call configured first-party handler paths.

No live network, provider, Cloudflare KV, OAuth credential or user account used. Full original Vitest suite **not executed**, because monorepo JavaScript dependencies are not fully installed/qualified on this Mac.

## Explicit no-go boundary

**This does not enable public OAuth.** Wave151's `flindOAuthRuntimeReady(env, REGION_BASE_URLS)` gate still refuses every external OAuth route with 503 because the remaining real handler destinations in `constants.ts`, register, authorize, token, JWKS, introspect and userinfo are not migrated or OIDC/PKCE qualified. Do **not** remove or bypass the gate. Continue staged, tested first-party backend/issuer/PKCE/token ownership migration under #5 and real full product E2E under #82.

Repository private, inherited GitHub Actions disabled, no publishing/deploy/paid services, mandatory LICENSE/NOTICE attributions preserved.
