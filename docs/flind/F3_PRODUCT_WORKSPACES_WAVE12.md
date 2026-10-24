# Flind F3 Wave 12 — product npm workspace identity migration

## Implementation scope

Source-first, exact-identifier-only migration of **37 internal product npm
workspaces** from the inherited npm scope to `@flind/products-*`. The
affected product families include billing, alerts, feature flags, dashboards,
error tracking, data warehouse/modeling, experiments, cohorts, AI
observability, logs, endpoint tooling, MCP products, marketing analytics,
and related internal packages.

Migration updates the internal package manifests, downstream import
specifiers, pnpm importer keys and build/test references together. All
37 migrated manifests are explicitly `private: true`. No source algorithm,
Django migration, database table, API route, externally published package
identity, or OS installer binary path was intentionally changed.

## Executed verification on macOS, 2026-10-24

- Workspace graph check: **260 internal workspace dependency edges**, zero
  unresolved, status **PASS**.
- Flind-named tracked npm manifests increased from **33 to 70**.
- Inherited-scoped first-party npm manifests decreased from **126 to 89**.
  The full package-name migration gate therefore still **FAILS**.
- `pnpm install --lockfile-only --offline --frozen-lockfile --ignore-scripts`
  using **Node 24.15.0** **PASSED**, with the original
  `trustPolicy: no-downgrade` intact and **3,982 supply-chain entries**
  verified. This is **not** a package installation or application build.
- `PYTHONPATH=. python3 -m unittest discover -s tools/flind
  -p 'test_*.py' -q`: **182 tests PASS**, including five new
  exact-identity, manifest privacy, lockfile, dependency-graph, and
  tracked-text regression checks.
- `git diff --check` and the Flind foundation checks are separate
  source-level gates.

## Remaining release qualification

This wave alone does not qualify real TypeScript bundling, Jest, the app's
package installation, Django migrations, API ingestion, browser journeys,
SDK resolution by a customer, live network egress, binary identity, or
license/provenance requirements. Do **not** enable inherited CI workflows
or deploy the private repository. **Release remains NO-GO.**
