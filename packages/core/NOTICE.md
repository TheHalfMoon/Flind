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

This core is used by the private staged @flind/node SDK, not a fully
independent or published production SDK. Its type imports are mechanically
redirected to the private, byte-preserved @flind/types workspace package.
Original upstream identity and licensing remain in UPSTREAM_PACKAGE.json,
LICENSE and the pinned archive. No publish, deploy or full independence
claim without explicit GREEN LIGHT FLIND.
