# Flind SDK health navigation: owned docs or no external link

Status: **local source-contract qualification 3/3 passed**. The exact-head Jest,
TypeScript and GitHub contract gates must pass before merge.

## Scope and privacy risk

The SDK Health report and Health page issue renderer exposed a separate set
of inherited SDK release and documentation links outside the SDK onboarding
selector. The legacy `SDK_DOCS_LINKS` table contained **31 SDK entries**
pointing to a third-party GitHub organization and documentation domain,
including JavaScript, Python, Node, mobile, MCP and game-engine SDKs.
Clicking an SDK warning led to an unowned website.

This change preserves the existing 31 telemetry SDK identity keys and
readable SDK names. Its runtime navigation table derives documentation
links from `flindDocsUrl('libraries/...')` and release links from
`flindPublicUrl('changelog')`. These centrally validate an operator-provided
Flind-owned **HTTPS hostname**. If the hostname, documentation root, or
changelog are not configured, **the links are hidden** and each diagnostic
surface displays inline explanatory text instead. It does not substitute
PostHog, GitHub, or other providers as a fall-through link.

These guards are applied to:
- the SDK Health version table (Releases / Docs / Updating);
- the SDK Health warning banner (Learn how);
- the Health page's outdated SDK issue detail (Releases / Docs).

All version tables, status signals, migration hints, scan actions and alert
functionality remain intact; only outbound navigation changes. The actual
Flind docs pages and SDK releases are **not yet live**. A configured URL
indicates an owner-approved origin, not evidence that an individual
documentation page exists or that a package has been independently released.

## Verification

`node --test frontend/bin/flind-sdk-health-owned-navigation.test.mjs`
asserts 31 compatible SDK choices, exclusively guarded first-party URL
construction, no inherited external navigation in the three live UI
surfaces, and actionable fallback text without an owner URL.

The branch triggers the standard Flind frontend Jest/TypeScript gate and
a dedicated dependency-free source-contract gate. The exact-head CI
and representative browser evidence should be checked before merge.

This is not a system-wide no-egress audit. Other onboarding flows,
third-party SDK runtime telemetry, external source links, generic help
widgets and embedded bundles require separate review. Do not redistribute
public packages, deploy, tag or publish until the explicit founder
`GREEN LIGHT FLIND`. Preserve legally required third-party source
licenses, authorship and notices.
