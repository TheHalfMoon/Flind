# F3 Wave 3 — dependency-free pnpm workspace graph gate

A large copy-first product cannot safely rename internal npm package scopes
without accounting for every `workspace:*` dependency. Changing names alone
can break package filters, importers and test tools.

## Command

```bash
python3 tools/flind/check_workspace_links.py
```

This runs without `node_modules` or a network connection. It checks tracked
`package.json` manifests for:

- Unique active root-workspace package names (duplicate independently vendored
  GitHub/Depot action names are not treated as root workspace collisions).
- Resolvable exact `workspace:*` dependency names in dependencies,
  devDependencies, optionalDependencies and peerDependencies.
- `private: true` for every renamed `@flind/*` workspace package.
- Explicit distinction between workspace graph integrity and tracked first-party **npm package-name** identity completion only.

For a deliberate **strict npm-package-identity check**, run:

```bash
python3 tools/flind/check_workspace_links.py --require-no-legacy
```

The strict npm-package-identity check currently exits **2**, not 0, because substantial
first-party workspace package migration remains. Even when all npm package names have migrated, the separate source-wide
brand audit must still pass. Do not confuse a clean dependency graph or a
clean package-name check with a finished standalone Flind product.

## Baseline (2026-10-24)

- 169 tracked package manifests; 165 unique package names.
- 260 named `workspace:*` dependency edges; 0 unresolved edges.
- 0 conflicting active package names.
- 0 unprotected renamed `@flind/*` packages.
- Five Flind-named packages are present, including the prior
  `@flind/announcements-admin` and four workspaces renamed in F3 Waves 1–2.
- 154 legacy-scoped first-party package IDs remain.

The validator has tests for missing links, duplicate names, unprotected
Flind packages, nested isolated CI action name collisions and the negative
strict-identity case.

This is a **source-only** graph guard. It cannot substitute for a frozen
lockfile install, compiler/typecheck, full frontend and backend tests,
browser journeys, migrated data, or packaging. Release remains **NO-GO**.
