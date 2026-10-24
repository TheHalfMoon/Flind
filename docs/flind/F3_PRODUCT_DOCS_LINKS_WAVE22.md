# F3 Wave 22 — product help must not advertise another service

## Risk and decision

Flind's product manifest catalog and scene registry offered inherited
vendor-specific documentation URLs in 38 product and core scene entries.
The original source contains useful implementation but those documentation
pages are not Flind documentation, and sending Flind users to another
vendor's help center is not acceptable as a product default.

**No Flind documentation host has been qualified or published.** Accordingly
the inherited links are removed rather than replaced with a fabricated
or unowned domain. UI components that use the optional `docsHref` contract
will hide their help link until a verified Flind-owned link is configured.

## Atomic source and output migration

- Remove 29 inherited documentation links from 22 product manifest files.
- Remove the matching 29 links from checked-in generated
  `frontend/src/products.tsx`. This file is generated from the manifests
  and must not be hand-edited independently of them.
- Remove nine inherited scene links from `frontend/src/scenes/scenes.ts`.
- Retire the stale sidebar test/allowlist that explicitly required inherited
  vendor docs. Preserve the descriptive product metadata behavior.
- Preserve actual feature behavior, scene identifiers and navigation URLs.

## Evidence and deferred gates

The Python regressions ensure the source manifests and checked-in generated
configuration have no inherited `docsHref` literals and that the sidebar
tests no longer assert old vendor URLs. TypeScript syntax parsing checks
the touched TS/TSX files. The wider Python suite must pass.

The full `frontend/build-products.mjs` regeneration was not performed on
this lightweight checkout because its frontend build dependencies are not
installed. A deterministic actual generator rerun, Jest, TypeScript type
check and browser verification remain mandatory before release. Do not call
this a complete documentation migration until real Flind docs exist.

Keep GitHub private and Actions disabled. No publishing or deployment.
