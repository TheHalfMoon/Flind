# Onboarding SDK documentation ownership and optional-link behavior

Status: **source-level checks passed locally; full Jest/TypeScript and
migrations/ratchet require exact-head GitHub CI**.

## Problem

The in-product SDK selector listed **93 direct links to the donor provider's
documentation domain**, including AI observability and common web, server,
and mobile SDK choices. Installation guidance was otherwise presented
as part of Flind's first-party application.

This was a user-initiated **external navigation leak**, not proof that
events were automatically sent to the donor. However it contradicted the
operator-owned Flind documentation policy and created confusion during
setup. Error tracking and session replay also supplied direct donor
documentation overrides. The SDK help component always rendered a
clickable link even if the destination was not owned.

## Change

- For every SDK catalog entry, preserve its named SDK, feature tags,
  selection state, image, and install handler, but derive its docs
  destination through the existing `flindDocsUrl(relativePath)` exact-host
  HTTPS guard. No custom domain or invented absolute Flind URL is added.
- Without a configured `VITE_FLIND_WEBSITE_HOST` and matching
  `VITE_FLIND_DOCS_URL`, catalog docs links are empty and the
  SDK wizard shows ordinary text that documentation is unconfigured.
  Installation instructions and API/SDK choices remain accessible.
- Error tracking's Convex documentation override and session replay's
  Unity override use the same first-party guard.
- Regardless of which feature-specific override a caller supplies, the
  SDK selection helper rejects any destination failing
  `isOwnedFlindDocsDestination`, preventing accidental reuse of a donor
  or unrelated remote URL.
- Update existing Jest test expectations to use the derived first-party
  link or the absent-link empty string, and retain the SDK selection
  behavior; a cheap dependency-free contract adds extra regression checks.

## Acceptance evidence required

`node --test frontend/bin/flind-sdk-catalog-docs-owned.test.mjs`
proves all 93 catalog entries derive links through the owner guard,
tests conditional link rendering and validates the override policy in
source. It does **not** execute the React component or TypeScript
compiler. Exact-head full frontend Jest, TypeScript diff check,
database migrations and rename ratchet must all pass before merging.

The presence of a configured docs root does **not** prove every deep
page is published; real publishing/content and link-checking remain
separate release tasks. Other onboarding settings pages and donor
Cloudinary-hosted logos are **outside this PR**. Do not misrepresent
those as cleared.

No public deployment, release, tag, package publication or installer
distribution without explicit `GREEN LIGHT FLIND`. Preserve required
third-party legal notices and provenance separately from application
navigation.
