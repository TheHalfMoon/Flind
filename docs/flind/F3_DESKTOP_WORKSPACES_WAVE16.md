# F3 Wave 16 — migrate 17 internal desktop npm workspaces

## Implemented

Rename 17 first-party internal npm package IDs under
`products/desktop/apps`, `products/desktop/packages`, and
`products/desktop/tooling` to the Flind npm namespace, updating exact
internal imports, TS config aliases, dependency manifests and lockfile keys.

- Applications: code, mobile, web, and `mobilehog` renamed to
  `@flind/mobile-studio` rather than retaining the old brand token.
- Internal libraries: API client, core, DI, Electron TRPC, host router/TRPC,
  platform, shared types, UI, workspace client and server.
- Tooling: TypeScript and tsup configuration.

All migrated manifests are now explicitly `private: true`. No intentional
changes to APIs, Electron bridge contracts, filesystem layout, data
persistence, billing, model inference or compiled application branding.

The change touches about 3,029 tracked source files with ~11,913 exact
package ID references. This is a large dependency-migration patch; do not
interpret source graph checks as a qualified Electron distribution.

## Evidence, macOS 2026-10-24

- Original named packages: 139 Flind-scoped, 20 inherited. After migration:
  **156 Flind-scoped, 3 inherited**.
- Internal workspace graph: **261 dependency edges**, zero unresolved.
- Node v24.15.0 frozen offline pnpm lockfile-only check **PASS** using the
  unchanged supply-chain trust policy, **3,981 entries**.
- Five new standard-library Python assertions validate private manifest
  names, desktop imports, internal links and integrity of an external
  published MCP dependency.
- Total Flind Python suite and foundation identity checks are mandatory
  premerge checks.

## Outstanding release qualification

The remaining three inherited npm workspace IDs include the frontend
design library, Node ingestion service and MCP server. Their dependencies
must be evaluated carefully: the lockfile also references a **published**
`@posthog/mcp@0.23.0` dependency that cannot be blindly rebranded.

Desktop TypeScript monorepo builds, Electron/native loading, installer
runtime, macOS/Windows/Linux journey tests, user-data migration, external
DNS/HTTP egress and complete source/binary identity audits have not passed.
The project remains private; GitHub Actions disabled; **release NO-GO**.
