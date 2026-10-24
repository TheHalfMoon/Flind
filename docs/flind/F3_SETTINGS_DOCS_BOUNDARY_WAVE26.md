# Wave 26 — Flind settings must not send users to inherited documentation

## Observed risk

SettingsMap exposed 58 copied source documentation links to the upstream
vendor. These were shown as user-facing Docs links in Flind settings. Flind
documentation for each feature has not yet been independently provisioned.

## Implementation

- Remove the 58 vendor docsUrl fields from the source-of-truth settings map.
- Preserve the optional docsUrl interface and the UI's conditionally rendered
  help link; missing destinations do not create an external navigation.
- Preserve Slack, GitHub and Linear provider-specific documentation references;
  those are factual third-party help destinations rather than upstream product
  branding.
- Replace the visible snippet description with Flind identity.
- No new documentation URL has been invented, published or deployed.

## Qualification

- Scoped Python tests prevent upstream Docs URLs returning to settings metadata.
- Settings map TypeScript/TSX parsing passed with zero syntax diagnostics.
- The full Flind Python regression suite is required before merge.
- Frontend Jest, E2E browser navigation, accessibility and source-generated
  frontend builds were not run in this lightweight local checkout.

This is not full web branding or release qualification. The inherited
dependencies, database/API contracts, frontend/browser testing, SDK and
outbound-network audit remain open. Repository private, Actions disabled,
no publishing or deployment. Preserve required attribution.
