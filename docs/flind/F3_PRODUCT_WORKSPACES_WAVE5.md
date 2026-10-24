# F3 Wave 5 — twenty low-impact Flind product workspace identities

This wave migrates **npm workspace identity only**, not Python modules, URL
routes, storage schemas, APIs, business logic or legal/provenance notices.

## First-party packages migrated

The following `products/*/package.json` package IDs have moved from the
inherited npm scope to `@flind/products-*`:

- access-control, account-audits, aeo, ai-gateway, ai-training
- analytics-platform, apm, approvals, authorization, batch-exports
- commands, context-layer, core-events, data-tools, demo
- event-definitions, exports, field-notes, games, links

All twenty are explicitly `private: true`, including minimal manifests
which previously had no `private` field.

Exact package-name references in the frontend workspace manifest, pnpm
importers, build metadata and searchable source files have been migrated.
Existing `workspace:*` dependency specifiers and directory paths are
preserved.

## Current verified workspace evidence

- `python3 tools/flind/check_workspace_links.py` reports **169** package
  manifests and **260** linked workspace dependency edges with zero
  dangling references.
- First-party `@flind/` workspaces increase from **13 to 33**.
- Unmigrated first-party inherited-scoped package IDs decrease from
  **146 to 126**, and the strict npm package-name completion gate remains
  **FAIL**.
- Regression checks validate package names, nonpublishable manifests, frontend
  dependency references and lockfile importer keys.
- Tests from earlier waves now use monotonic migration expectations;
  completing a later migration must never be flagged as regression merely
  because the remaining old-name count decreased.
- This is a source and dependency-graph check, not an application runtime
  compatibility or end-to-end check.

## Qualification still required

The frozen **lockfile-only** check under **Node 24.15.0** with
`pnpm install --lockfile-only --offline --frozen-lockfile --ignore-scripts`
**PASSED**, verifying all **3,982** supply-chain policy entries without
weakening the repository's trust policy. This is not a full npm installation.
Next, complete actual dependency installation, typecheck, unit tests, first-party browser journeys, Django
tests, persistent-data migration checks and OS distribution builds.
Those full-stack gates remain unproven and release status is **NO-GO**.

Do not disable integrity enforcement or deploy Flind yet.
