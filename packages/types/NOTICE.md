# Flind staged SDK type definitions

This is a **private, unpublished** Flind compatibility staging package (`@flind/types@1.421.0`), intended for future validated migration of Flind SDK dependencies. It is not included in the production pnpm workspace or lockfile, and it is not wired to consumers in this PR.

## Original source and preservation

The complete published archive of `@posthog/types@1.421.0` (78 original files) was used as the pinned source.

- npm archive: `posthog-types-1.421.0.tgz`
- npm SHA-1: `ce6d1c0a8a132bec9774aca16937b0656335a781`
- npm Subresource Integrity: `sha512-KP34CqgRYYyp3wU77OixL0URb2ildKM+QxBOXtQ4YYaa1ARTt3looxkn/w8gwKo6gWZg2VW/DgSoqAW4XeDAPQ==`
- The original published `package.json` is preserved, **byte-for-byte**, as `UPSTREAM_PACKAGE.json`.
- All original `src/`, `dist/`, `LICENSE`, and `README.md` contents are preserved exactly.
- Only the active `package.json` has Flind private name, repository/contact metadata, and provenance files added. The exports, entrypoints, version, and dev tooling metadata stay compatible.

Copyright and licensing remain with the original rights holders, under the original complete `LICENSE`. The Flind package name and staging documentation do not imply a change in copyright or an upstream endorsement.

## Release gates

Run `node .github/scripts/flind-types-parity.mjs <expanded-original-package-directory>` locally, or use the isolated Flind types GitHub workflow. Do not add this package to the production workspace or replace `@posthog/types` dependencies without separate CJS, ESM, TypeScript, Node/browser, privacy, and ingestion qualification. **No deployment, package publication, app release, binary, or tag** without the existing `GREEN LIGHT FLIND` release decision.
