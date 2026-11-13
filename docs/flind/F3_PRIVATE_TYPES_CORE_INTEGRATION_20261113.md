# Flind private core-to-types workspace integration

**Scope:** private SDK dependency migration, not a production deployment or npm publication.

- Core dependency: `@flind/types: workspace:*`; pnpm workspace and lockfile link.
- Only donor-named *type imports* in core TypeScript source and `.d.ts` declarations become `@flind/types`. Compiled CJS/ESM executable files remain unchanged.
- Full original `src/dist/surveys` file parity remains testable: only exact type-name substitutions are allowed. Original complete LICENSE, upstream package manifest, provenance and types package source are preserved.
- Private active `@flind/types` drops inactive original build scripts/development dependencies, but the original manifest stays in `UPSTREAM_PACKAGE.json`.
- Exact-head workflows check core CJS/ESM subpath ABI, Node SDK host and loopback safeguards, locked workspace, TypeScript 7 declaration imports, types archive SHA512, rename ratchet, and live database migration idempotency.

## Local checks

- Windows Node 24: private Node SDK qualification **3/3 PASS**.
- Core CJS/ESM exported ABI smoke **2/2 PASS**.
- Strict TypeScript 7.0.2 Flind core/types consumer imports **PASS**.
- Pinned 78-file types source/license/CJS/ESM parity **PASS**.
- Complete original-source byte parity must be checked in Linux CI because a Windows checkout rewrites original LF to CRLF. The original license bytes in Git are unchanged; do not relax original legal/byte checks.
- Root pnpm lockfile verification was interrupted by slow unrelated registry supply-chain metadata fetching, and the importer changes were reduced to the core/types relationship. Exact-head Linux frozen-lockfile CI is required.

**Release NO-GO.** This does not verify standalone ingestion, auth/tenant isolation, migrations with real user data, backup/restore, deployment artifacts, or removal of remaining externally hosted dependencies. No deployment, package publication or tag without explicit `GREEN LIGHT FLIND`.
