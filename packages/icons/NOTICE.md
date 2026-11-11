# Provenance

Vendored from the npm package `@posthog/icons` 0.39.0 (MIT, Copyright (c) 2023 PostHog Inc.), as part of Flind's
rename of PostHog's published packages (`flind/rename/PLAN.md`, stage 3). Its MIT license and copyright notice are
kept unchanged in `LICENSE`.

The package's source repository (`PostHog/icons`) is not public, so the published build is vendored as is:
`dist/` is the npm tarball's `dist/` directory, byte for byte. The bundle files keep their upstream names
(`posthog-icons.es.js`, `posthog-icons.cjs.js`) because each ends with a `sourceMappingURL` comment naming its map
file; renaming them would break the source maps or require editing the build.

## Flind changes

Flind's own entry files wrap the build: `index.mjs` (ESM), `index.cjs` (CommonJS) and `index.d.ts` (types). They
re-export every upstream icon and replace one:

- `IconLogomark` was PostHog's hedgehog logomark. It is replaced by Flind's mark from `frontend/public/flind-icon.svg`
  (rounded tile, "F", accent dot), drawn in a single colour: the tile is filled with `currentColor` and the "F" and dot
  are knocked out. It accepts the same props as upstream icons (`LemonIcon` class, `width="100%"`,
  `fill="currentColor"`, caller props win), with a `0 0 64 64` view box.

## Candidates for a later Flind redesign

These upstream icons depict PostHog product artwork rather than the company logo, so they are kept unchanged for now:

- `IconDeskHog`
- `IconHogQL`

## Icon artwork licensing

The upstream README states that the icon artwork comes from the Central Icons library (iconists.co), used by PostHog
under an Enterprise license, and asks that its preview site not be shared. The npm package itself is published under
MIT. On 2026-11-11, the Flind founder stated that they possess full authorization to copy, use, and rebrand the artwork
and source for Flind. This is a founder authorization representation, not an independently verified sublicensing finding;
its underlying permission documents are not stored in this repository. Original third-party attribution remains intact.
