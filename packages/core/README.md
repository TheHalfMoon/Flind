# @flind/core

Private, full-source and distribution staging of `@posthog/core@1.64.1`,
renamed at the npm package boundary to `@flind/core`.

This copy preserves the published CommonJS/ESM and TypeScript API
entrypoints, including `/error-tracking`, `/surveys`, `/testing`,
`/utils`, and `/vendor/*`. No source or runtime symbols are arbitrarily
removed. Exact pinned export parity is an explicit GitHub CI gate.

The package is intentionally **not a root pnpm workspace dependency yet**
and is **not published**. Existing Flind Node and React SDKs are unchanged
until their imports, type dependencies, locked dependency graphs, isolation
and real-ingestion contracts pass a dedicated migration. This staging
prevents breaking production runtime compatibility while validating the
source-first transplant.

The original LICENSE and UPSTREAM_PACKAGE.json are included verbatim and
NOTICE.md explains provenance. Original public API names remain while
functionality and private use are evaluated. This does not prove an
independent browser SDK, network isolation, ownership of hostnames or a
finished Flind release.
