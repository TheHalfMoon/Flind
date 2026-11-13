# Flind SDK framework installation help: first-party or fallback

Status (2026-11-14): **local Node source contracts 4/4 pass**.
Exact-head frontend Jest/TypeScript and GitHub source checks are required
before merge.

## What changes

The existing SDK setup forms for Nuxt, Vue and Flutter contain direct
clickable links to a third-party provider's documentation. Flutter,
Android and iOS code examples additionally included old vendor
documentation URLs as copyable comments. This creates unnecessary
off-platform navigation and confusing instructions when a developer
expects a self-hosted, independently branded Flind system.

This change preserves the existing steps and executable SDK code
examples, while restricting user-facing documentation navigation to
the validated `flindDocsUrl` and `flindDocsSectionUrl` helpers:

- Nuxt 2.16 fallback documentation is first-party or descriptive text
- Vue 2.7 fallback documentation is first-party or descriptive text
- Flutter screen-observer explanation links to the configured Flind
  documentation or renders the exact `PosthogObserver` compatibility
  class name as inline code, never an external donor link
- Android, iOS and Flutter replay configuration comments no longer
  tell users to consult an inherited provider website

No new URLs, tracking hosts, installers or third-party network requests
are introduced by these changes.

## Limits

The copied SDK *package identifiers* and API compatibility names in
the original examples are **not** independent Flind packages. The
original iOS and other SDK installer/package-manager instructions
are not yet qualified for public release. These instructions must be
independently validated for package availability, release ownership,
privacy and provenance before use outside engineering tests. This
change does not claim that the referenced Flind docs pages exist.

The branch triggers full Flind frontend Jest/TypeScript checks and an
explicit source contract with four local checks. The web workflow
must be green at the exact head before merge.

No public SDK, CLI installer, tag, deployed service, mobile binary or
production release without explicit `GREEN LIGHT FLIND`. Preserve
required third-party licenses and source attribution.
