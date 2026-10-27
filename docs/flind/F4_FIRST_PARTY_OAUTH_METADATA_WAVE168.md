# Wave 168 — Client-visible OAuth metadata extensions use Flind identity

## Behavior change

The first-party Flind OAuth proxy rewrites backend OAuth/OIDC standard endpoint URLs to its own public issuer, while retaining the actual regional URL for the extension that identifies the backend region. Before this wave, two **non-standard, inherited** JSON metadata extension keys (`posthog_region`, `posthog_base_url`) were surfaced unchanged to clients, despite the Flind-only product identity.

Wave168 maps these two upstream-compatible keys to `flind_region` and `flind_base_url` in client-facing discovery documents. It retains the regional origin as the `flind_base_url` **value**, not as an endpoint to proxy. For all other nested endpoint URL values it retains the established rewrite to the Flind OAuth issuer. The key mapping is recursive in objects and arrays. If the backend already emits native Flind extension keys alongside inherited aliases, the native Flind values win. **Standard OAuth/OIDC fields** (`issuer`, `authorization_endpoint`, `token_endpoint`, `jwks_uri`, `scopes_supported`, `code_challenge_methods_supported`, etc.) remain unchanged, except their existing Flind endpoint rewriting.

Legacy names exist only as an **upstream compatibility input** in the transformer; they are no longer emitted as these two metadata extension keys in the transformed discovery document. This is not a global source or artifact legacy-string clearance: other services, metadata values, SDKs, manifests and required legal attribution remain independently scoped. Clients using inherited nonstandard extension keys will need to migrate to the first-party names. The repository is private pre-alpha; no public client migration or release has been performed.

## Original service qualification — 2026-10-27

The exact proposed source and tests were executed on the existing isolated, no-cost Mac Node/TypeScript OAuth service runner.

- Original complete OAuth Vitest suite: **132/132 PASS across 14/14 test files**; previous Wave163 suite was 130/130, this wave adds two first-party metadata regressions.
- Strict `tsc --noEmit --project tsconfig.json`: **PASS, zero diagnostics**. The implementation avoids `Object.hasOwn` because the pinned TS target lacks it.
- New regressions cover recursive extension translation while preserving OIDC/OAuth endpoint names, Flind owner value precedence when both aliases exist, explicit regional URL preservation, and absence of inherited extension keys from the response payload.
- All regional fetch, PKCE, metadata and key material in tests are synthetic mocks; no production IAM, Cloudflare deployment, user data or customer authorization codes were contacted.

## Remaining gates

The Wave151 public Worker ingress safety gate remains closed. This PR **does not** qualify real Flind-owned OAuth provider/PKCE/JWKS, or live Django, DB migrations, Redis/Kafka/ClickHouse ingestion, tenant-scoped API/dashboard, browser/desktop E2E, final source/SDK/binary naming audit, or release. Keep #5 and #82 OPEN, release NO-GO. GitHub private, inherited Actions disabled, no deployment/publication/paid services, preserve legally required third-party notices.
