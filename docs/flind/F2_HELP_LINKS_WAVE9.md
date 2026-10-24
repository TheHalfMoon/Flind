# Flind F1/F2 — first-party help and support links

## Why

Core help menus and support panes inherited public documentation, community,
changelog, roadmap, and cloud-upgrade links from the source product. Flind has
not yet published these resources at independently controlled addresses. A
private source repo is not a substitute for a public docs site.

## Implemented

- `frontend/src/lib/flindPublicLinks.ts` validates optional external
  Flind destinations against `VITE_FLIND_WEBSITE_HOST`. No host or URL
  is assumed by default.
- Explicit settings: `VITE_FLIND_DOCS_URL`, `VITE_FLIND_CHANGELOG_URL`,
  `VITE_FLIND_COMMUNITY_URL`, `VITE_FLIND_ROADMAP_URL`.
- Only absolute HTTPS links to the **exact** configured first-party hostname
  can be shown. Credentials, alternate ports, fragments, and lookalike
  hostnames are refused.
- Converted the primary Help menu, scene menu bar, Today menu, Today support
  pane, and legacy side-panel support pane. Missing destinations are hidden,
  not replaced with fictional Flind links.
- Removed the inherited cloud-upgrade menu shortcut from the local help menu.
- Replaced direct inherited vendor support/community buttons and misleading
  claims about the current volume of forum conversations and AI support.
- Added source and TypeScript unit tests.

## Verified

- Source checks in `tools/flind/test_public_help_links.py`.
- Parsed all 7 modified TS/TSX files with TypeScript 5.9.3.
- Executed the standalone URL validator with 15 allow/deny assertions.
- `git diff --check` passes.

## Still required before release

- Run real frontend type-check, Jest/Vitest and browser E2E.
- Build and publish actual Flind docs, changelog, community and roadmap
  before configuring their corresponding URLs.
- Audit all remaining third-party links elsewhere in the UI, including
  secondary support actions, status feeds and product documentation.
- Run backend egress tracing, SDK/package migration and full release gates.
- The strict zero-identity source and distribution gates remain FAIL.
- No production launch or publication.
