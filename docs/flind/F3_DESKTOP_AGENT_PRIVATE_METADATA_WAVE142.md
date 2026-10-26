# Wave 142 — Flind private Desktop and Agent package identity

## Changed, metadata only

Three already-first-party private `@flind/*` package manifests still showed the upstream brand or upstream company identity:

- `products/desktop/apps/code/package.json`: description, maintainer and homepage now identify Flind. The homepage uses the actual existing private Flind GitHub repository, not an invented deployment.
- `products/desktop/packages/api-client/package.json`: description now identifies the Flind API without changing HTTP configuration, auth routes or protocol behavior.
- `packages/agent/packages/agent/package.json`: description, maintainer and repository metadata now identify Flind, while the Git-based task and Claude Agent SDK functionality are unchanged.

**No changes** to package names, dependencies, dev dependencies, scripts, exports, license identifiers, executable code, endpoints or lockfiles. Preserved historical copyright/third-party legal attribution in root and Desktop LICENSE files.

## Executed checks

Fetched the exact GitHub PR branch into the connected Mac's existing clean sparse checkout without modifying its branch. Executed `tools/flind/test_private_workspace_metadata_wave142.mjs` under Node24 with `FLIND_SOURCE_ROOT` and `FLIND_TEST_REF=FETCH_HEAD`. It compares all three current manifests with the immutable prior merged Wave141 baseline `7f263af2983b947dc421a9283d89351f8f5746db`.

**PASS, process exit 0:** all three manifests are valid JSON, `private=true`, `@flind/*`; only approved display metadata fields changed, their new values contain no upstream name; existing runtime/build/dependency and legal fields are equal; root and Desktop LICENSE content is byte-for-byte preserved.

## Deferred identity migrations

The remaining private manifests, other source text, SDK names, Django imports/migration labels, OAuth identity, external gateway routing, release action publishing targets, generated assets and screenshots are **not** automatically complete or rebranded by this change. Renaming protocol-bound identifiers without migrating their runtime consumers would break the product. Continue staged source audits under #5, and actual integration/runtime E2E under #82. Release NO-GO.

The repository remains private, inherited Actions disabled, no publishing/deployment/paid services; legal attribution remains in the appropriate notices.
