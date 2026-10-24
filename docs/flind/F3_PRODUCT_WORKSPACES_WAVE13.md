# Flind F3 Wave 13 — remaining product npm identity migration

This wave migrates the **39 remaining** internal product-prefixed npm workspace
names from the inherited scope to Flind-owned package IDs. Source-first,
exact-match replacements propagate through manifests, code imports, pnpm
lockfile and build/test references.

Three package names contained old vendor terms even after merely changing
their npm scope. They were assigned first-party product identities rather
than carrying those old strings into the new package IDs:

- AI application workspace: `@flind/products-flind-ai`
- review tooling workspace: `@flind/products-review`
- stamping workspace: `@flind/products-stamp`

All migrated manifests are marked `private: true`. No directory movement,
Django schema migration, API route rename, runtime protocol modification,
or wholesale source replacement is performed in this change.

## Evidence from the Mac checkout, 2026-10-24

- Flind-scoped npm workspace package names **70 → 109**.
- Inherited-scoped first-party npm packages **89 → 50**.
- All **98** tracked product-prefixed npm workspace packages now use the
  first-party Flind scope; none retain the old npm product scope.
- Internal dependency graph: 169 tracked npm manifests, **260**
  workspace dependency edges, **zero unresolved**.
- Frozen lockfile-only validation under Node v24.15.0, offline, untouched
  `trustPolicy: no-downgrade`: **PASS**, 3,982 checked lockfile entries.
- Targeted source/manifest/lockfile regression tests verify all product
  packages are private, the renamed package IDs resolve, and no legacy
  product scope remains in runtime source imports.
- Flind's full dependency-free Python test suite and foundation brand
  entrypoint check are separate regression gates.

## Release-blocking limitations

Package-name migration alone does not establish that the application can
run: full JS dependency installation, frontend production bundle, Jest,
Playwright, Django/API and database migration tests, customer SDK builds,
runtime network capture, compiled package branding and cross-platform
installers are still necessary.

The **50** other inherited-scoped first-party npm packages, thousands of
historical source identities, and live externally hosted services remain
open. Do not publish Flind or enable inherited CI. **Release NO-GO.**
