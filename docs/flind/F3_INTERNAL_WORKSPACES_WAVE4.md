# F3 Wave 4 — Flind-owned build, replay, AI and product workspaces

## Scope

Copy-first **identity migration only**. Move eight owned package identities
and every corresponding exact import, alias, script and lockfile reference:

| Package source | New workspace ID |
| --- | --- |
| `common/esbuilder` | `@flind/esbuilder` |
| `packages/owners-yaml` | `@flind/owners-yaml` |
| `common/plugin_transpiler` | `@flind/plugin-transpiler` |
| `packages/llm-normalizer` | `@flind/llm-normalizer` |
| `common/replay-shared` | `@flind/replay-shared` |
| `common/replay-headless` | `@flind/replay-headless` |
| `products/annotations` | `@flind/products-annotations` |
| `products/customer_analytics` | `@flind/products-customer-analytics` |

All eight are `private: true`. The underlying module APIs, exported types,
relative directory layouts, database schemas, runtime payloads and source
algorithms remain unchanged.

### Changes propagated

- Frontend Vite, Jest, esbuild, type resolution and Python/TS source references.
- Cross-package replay import graph and the Node.js recording-rasterizer.
- AI-observability frontends and MCP server dependency/type imports.
- CI build filters, Dockerfiles, utility package imports and test fixtures.
- pnpm lockfile workspace importer dependency names and relative links.
- Products annotations and customer-analytics workspace dependencies.

### Verified source state

- The Python workspace graph gate finds 169 tracked package manifests, 260
  `workspace:*` dependency edges and **zero unresolved workspace edges**.
- All eight migrated packages are discoverable with `pnpm --filter`; none
  is publishable as a package by default.
- The number of Flind-named first-party workspace packages increased to
  **13**; **146 inherited-scoped package IDs remain**.
- Tests include checks for manifest identity/privacy, relative lockfile
  paths, downstream imports, workspace graph completeness and no remaining
  exact legacy names for this wave in tracked searchable sources.

## Runtime qualification and blockers

- The Mac's default Node v26 does not meet the repo's declared
  `>=24 <25` requirement; a separate Node v24 installation is present.
- The first **offline** `pnpm install --lockfile-only --offline --frozen-lockfile
  --ignore-scripts` attempt failed due to unavailable trusted metadata
  (not a package graph error).
- A bounded **online metadata check** under Node **v24.15.0** using
  `pnpm install --lockfile-only --frozen-lockfile --ignore-scripts
  --prefer-offline` **PASSED** with the repository's original
  `trustPolicy: no-downgrade` unchanged. Pnpm verified **3,982 lockfile
  entries** against its supply-chain policies. No full package installation
  or build was undertaken.
- Full frozen-lockfile **installation**, frontend typecheck, TypeScript/Jest,
  Storybook/Playwright, Django, database and cross-OS packaging qualification
  have not been demonstrated.
- Source/binary independence and external-egress release gates remain FAIL.
  The Flind repository stays private; this wave does not publish the app.

**Release: NO-GO.** Do not treat correct package resolution as proof that the
product compiles, runs, or is safe to deploy.
