# F2 Wave 1 — Flind-owned defaults and outward-facing identity

## Changes

- Public login/sign-up metadata, structured data and canonical links now identify Flind and its configured SITE_URL, without importing a third-party image or organization profile.
- FLIND_HOST replaces the legacy transactional-email host setting and defaults to SITE_URL or local development origin; explicit HTTPS remains mandatory for sends.
- Cross-region project-connection origins have **empty defaults** and must be intentionally configured. Existing code validates that unconfigured targets do not resolve.
- Temporal UI default now points to localhost. The OpenAPI server list advertises the Flind instance rather than a separate SaaS vendor.
- Mobile telemetry configuration is opt-in: the sample key and upstream destination were deleted, the module and test were renamed to flindAnalytics, and the provider mounts only when both an API key and a destination are configured.
- Desktop announcements admin uses Flind-owned OAuth, API and telemetry settings. Missing analytics key or host produces no client capture.
- The metrics agent's default destination and matching golden render fixtures now use a local endpoint instead of a third-party hosted collector.
- A tracked-file inventory and strict zero-identity release gate are available through tools/flind/brand_audit.py.

## Verification

- 17 standard-library static tests PASS.
- 8 prior entrypoint checks PASS.
- Nine touched TS/TSX files passed TypeScript 5.9.3 syntax transpilation (syntax only, no type checking).
- Touched Python files passed py_compile.
- Staged git diff --check PASS.

## Scope and blockers

This is a **partial containment**, not proof of zero outbound traffic, security certification, full feature parity or release readiness. The Python/Django integration suite, actual mobile Vite/Expo runtime, Helm render tests, TypeScript type checking and full-stack egress trace have not been executed on a configured environment. Do not enable imported CI workflows automatically.

The full source still has thousands of legacy module/package/file identifiers. These must migrate in coherent dependency slices with generated lockfiles, database migrations and API compatibility tests. The zero-identity checker intentionally fails until that project-wide conversion is complete.

The baseline count was 31,192 matched tracked text files and 7,089 paths with legacy identity. The user-facing product MUST NOT be published while the brand gate is failing or code can send telemetry to an unowned destination.

## Next verified engineering units

1. Trace app-region redirects, hardcoded host lists, SDK and CLI endpoints; replace with configurable Flind hosts with allowlist tests.
2. Run a controlled DNS/HTTP tracing environment with all credentials absent and outbound access denied.
3. Produce and test locally a complete install/ingest/query/feature-flag flow.
4. Port SDKs under Flind package names with compatibility adapters only where data migration requires them.
5. Migrate persistent backend names, schema keys and package imports as atomic tested changes.
6. Replace remaining trademark assets and links, reconcile copyright notices and complete the repository-and-binary zero-identity gate.
