# Flind private core provenance

This private staged package is copied from the published npm tarball
`@posthog/core@1.64.1` for Flind's future independently managed SDK runtime.

- Published source: `@posthog/core`, version `1.64.1`
- Upstream repository: `https://github.com/PostHog/posthog-js`, `packages/core`
- Copied files: `src/`, `dist/`, `surveys/`, and the complete original `LICENSE`
- Original npm manifest: `UPSTREAM_PACKAGE.json` (preserved unchanged)
- Local changes: package name `@flind/core`, private staging metadata,
  README/NOTICE and qualification tests outside the package

The published manifest declares MIT, while the complete copied LICENSE
contains additional third-party Apache-2.0 and MIT notices for individual
files and components. Preserve the entire license text and any
file-specific notices. No ownership or relicensing of the original
copyrighted works is asserted.

This core package is not published or integrated into production yet.
`@posthog/types` remains an upstream type dependency until a separate
qualified migration. Do not publish, deploy or claim full vendor
independence without explicit GREEN LIGHT FLIND.
