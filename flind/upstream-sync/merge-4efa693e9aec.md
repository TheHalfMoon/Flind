# Upstream merge: cutoff `4efa693e9aec`

Flind main (`2ce3b1a`) merged with PostHog/posthog `4efa693e9aecb76ad4321120df2201414b41737b` (the pinned cutoff in
`cutoff.txt`), with the Flind import commit `cd26680c84533f65f43e1c7efc701bf792a5363a` as the merge base. The owner
chose one merge over area-by-area integration.

## Method

- Flind's history is not connected to upstream's (it was rewritten when the repository went public), so a plain
  `git merge` would import all of upstream's history. The merge was computed as a three-way file merge with the
  import commit as base and committed as one ordinary commit on top of `main`. No upstream commits are in Flind's
  history; the upstream commit ids are recorded here and in the commit message.
- Merge settings: `merge.conflictStyle=diff3`, `merge.renames=false`.

## Conflicts (912)

- **477 files upstream deleted or moved, that Flind had changed.** Where upstream moved the file (rename detection,
  50% similarity), Flind's changes were three-way merged into the new path (101 clean, 24 resolved by hand). The other
  352 were deleted upstream; their Flind edits were rebrand-only or belonged to removed features.
- **455 files changed on both sides.** 362 resolved by replaying Flind's token-level edits onto upstream's text where
  upstream left that region unchanged; 93 resolved by hand, keeping upstream's code and re-applying Flind's rebrand,
  legal-copy and runtime-independence changes.
- **Flind's security backports (#11–#17).** The 159 files those PRs touched were re-merged using Flind's version from
  before #11, so upstream's original fixes replace the adapted copies (125 clean three-way merges, 8 taken from
  upstream, no conflicts).

## Flind adaptations carried into upstream's new code

- Workspace packages keep Flind's names (`@flind/...`, map built from Flind's package.json names): module specifiers,
  `workspace:` dependencies, configs and `--filter` flags in upstream's new files were renamed. User-facing text and
  npm aliases that name PostHog's published packages were left as is. New upstream workspace packages got `@flind/`
  names (`@flind/hog`, `@flind/personhog-proto`, `@flind/toolbar-extension`, `@flind/mobile`,
  `@flind/products-knowledge-writer`, `@flind/products-ui-customization`).
- Migration: Flind's `1413_flind_rebrand_model_help_text` is now `1432_flind_rebrand_model_help_text`, after upstream's
  `1431_squash_2026_11_02_schema_addons`.
- Lockfiles regenerated from upstream's: `uv.lock` (`uv lock`; only the project entry changes), `pnpm-lock.yaml` and
  `products/desktop/pnpm-lock.yaml` (`pnpm@11.28.5 install --lockfile-only`). `bin/hobby-installer/go.sum` keeps Flind's
  removal of `posthog-go`.
- Domain Connect stays off by default in Flind; upstream's email-setup tests now enable it explicitly.
- The 10 workflows upstream added since the import are not taken (`ci-hoglang`, `ci-toolbar-extension`,
  `hogbox-preview-cleanup`, `hogbox-preview-env`, `mobile-build`, `mobile-ci`, `mobile-release`,
  `release-toolbar-extension`, `update-ai-costs-stale-alert`, `weekly-mcp-tool-health-report`). Flind runs only its own
  `flind-*` workflows; two of these publish releases, which stays on hold until the owner's GREEN LIGHT FLIND.

## Known follow-ups

- **Full rename.** The owner decided (2026-11-10) that everything becomes Flind: file and folder names, the Python
  package, JS packages, UI text, configuration, database tables (`posthog_*` to `flind_*` via migrations) and PostHog's
  published packages (vendored into this repository under Flind names, nothing published). It follows this merge as
  its own series of PRs. The `LICENSE` copyright notices stay, as the license requires.
- Upstream rebuilt the mobile app as `products/mobile`; Flind's mobile analytics change in the old
  `products/desktop/apps/mobile` did not carry over and needs re-porting.
  The new app also links PostHog's terms, privacy and support pages (`products/mobile/src/lib/legalLinks.ts`, used by
  the sign-in and settings screens); they must become configured Flind policy links before the app is built.
  `tools/flind/test_mobile_legal_consent_wave39.py` fails until then. The mobile app is not built or shipped.
- Several `tools/flind` guards not run in CI point at files upstream moved or deleted (status feed, website
  referrer, cloud boundaries, wordmark, old mobile app); they are updated or retired in the rename series.
