# Wave 33 — Reproducible Mobile and Mobile Studio local qualification

## Confirmed runtime failure

The copied nested Desktop lockfile conflated a first-party workspace package
(@flind/core, 1.0.0) with an external, independently versioned SDK package
(@posthog/core, versions 1.60.0 and 1.60.1). Four lockfile snapshot
dependency edges incorrectly pointed to @flind/core@1.60.x, which did not
exist in the package index or the workspace. This caused a real frozen
pnpm installation to stop with ERR_PNPM_LOCKFILE_MISSING_DEPENDENCY.

Corrected precisely those four third-party edges, in the snapshot blocks for
@posthog/browser-common, posthog-js, posthog-node and posthog-react-native.
The existing @posthog/core integrity records were already in the lockfile.
The first-party @flind/core workspace importer entries remain unchanged.
The Wave 16 internal-package identity test has a narrow exclusion for
only those versioned external registry edges, with Wave 33 assertions that
all four snapshot owners are correct. No general legacy-scope exception
has been added.

No fake package names or external package forks have been created. A
published dependency's original name is a package-resolution fact and
required provenance, not a Flind product-facing brand decision.

## Mobile ticket link recovery

Three original Vitest cases expected support-ticket links to the old
vendor cloud. A previous Flind mobile fail-closed configuration change
rightfully rejected those URLs, but unconfigured ticket link rendering then
threw instead of hiding the link. This wave:
- Uses explicitly configured Flind API origin fixtures in Vitest.
- Safely returns null for a support-ticket link if the Flind API host is
  missing or disallowed, rather than crashing the inbox UI.
- Verifies URL encoding and absence of inherited vendor destinations.

## Local test environment

Mac checkout: /tmp/flind-w12-20261024. Node v24.15.0, pnpm v11.28.5.
No cloud deployment, paid model/API calls or package publishing.

Fresh/partial install (from the nested Desktop workspace, not the root):

    cd products/desktop
    pnpm install --frozen-lockfile --ignore-scripts \
      --filter '@flind/mobile...' --filter '@flind/mobile-studio...'

The lockfile passed pnpm's supply-chain policy verification and the
installation completed. The agent has a SEPARATE nested workspace with
its own lockfile. The dependency build order, all executed successfully:
1. From packages/agent, install with frozen lock and --ignore-scripts,
   then run pnpm -r --workspace-concurrency=1 --filter
   '@flind/agent...' run build.
2. From products/desktop, build @flind/shared and @flind/platform.
3. Run tools/flind/qualify_desktop_mobile.py (or --skip-build if
   these exact prerequisites are already built).

This qualification script never installs packages, downloads tools,
publishes, deploys, calls model providers or enables GitHub Actions.
It stops on the first failed gate.

## Qualified evidence (local on macbook, 2026-10-24)

- Frozen/ignore-scripts installation for BOTH mobile clients: PASS.
- Flind Mobile original Vitest suite: 74 files, **708/708 PASS**.
- Flind Mobile Studio original Vitest suite: 15 files, **224/224 PASS**.
- Combined original Vitest: **932/932 PASS**.
- Mobile Studio TypeScript tsc --noEmit: PASS, zero errors.
- Mobile TypeScript existing baseline gate: PASS, **zero new errors**
  but **44 inherited TypeScript errors remain** in baseline. This is NOT
  equivalent to an error-free typecheck.
- Agent graph, shared and platform builds: PASS in correct dependency order.
- New Python regression ensures wrong third-party lock snapshot edges
  do not return and Flind first-party workspace entries remain unchanged.
- Full tools/flind Python regression suite: 281/281 PASS on macbook.
- Reusable local qualification script completed with exit code 0 after
  all four mobile test/typecheck gates executed.

## Still NO-GO

- Installed iOS/Android native builds, app-store identity and link ownership,
  OAuth callbacks, real device push, storage upgrade and logout, native UI E2E,
  mobile accessibility, backend/Redis/Postgres/Django and ClickHouse,
  ingestion and query correctness, full SDK/build graph and external egress
  tracing remain unqualified.
- At least 44 old Mobile TypeScript errors remain, despite baseline PASS.
- Third-party PostHog SDK dependencies still exist and must not be renamed
  to unpublished Flind packages as a cosmetic identity operation.
- Mobile asset/icon branding is incomplete; legal attributions retained.

Repo private, inherited GitHub Actions disabled, no production/release deploy.
