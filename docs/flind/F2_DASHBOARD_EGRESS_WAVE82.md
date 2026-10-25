# Wave 82 — Dashboard documentation egress is fail-closed

## Root cause

The dashboard's docs metadata was typed as
`PostHogComDocsURL` (a literal URL type hardcoded to the upstream
provider). The dashboard's `LearnMorePopover` used the metadata URL
directly, opening it in a new tab even when Flind had no configured
first-party public docs site.

Wave 82 changes **the boundary**, not just the labels.

## Implemented

- Migrate 18 Web Analytics dashboard tile/tab `docs.url` metadata
  references and 2 in-description help links from inherited URLs to
  Flind-owned, validated HTTPS docs paths and section anchors.
- Use a generic string for the dashboard's `Docs.url?` metadata
  rather than a hardcoded upstream-only literal type. This permits
  operator-configured Flind URLs and keeps missing links explicitly
  optional.
- Implement `isOwnedFlindDocsDestination` in the existing
  `flindPublicLinks` owner-validation module. It admits a link ONLY if
  its origin exactly matches the operator-configured HTTPS Flind docs
  origin and the path is beneath that docs root. It rejects vendor
  domains, subdomain lookalikes, custom ports, credentials, path
  prefixes resembling docs, query injections, malformed fragments,
  non-string inputs and absent docs configuration.
- The actual `LearnMorePopover` applies the runtime validator
  before rendering an external `Learn more` button; descriptions,
  internal actions and info controls remain functional when no docs
  are configured. This also protects inherited URLs originating from
  as-yet-unmigrated product/marketing tabs.
- No SDK, SQL schema, E2E harness, analytics query, licensing
  attribution, team records or deployment changed.

## Real tests — October 25, 2026

- **132/132 actual Jest tests PASS** across the large
  `webAnalyticsLogic.test.ts` suite and Flind URL validators,
  including new hostile URL and unconfigured-host cases.
- **5/5 Node24 + pinned TypeScript contract tests PASS** verifying
  20 migrated references, fail-closed popover behavior and parse
  integrity of modified modules.
- Oxfmt formatting and patch whitespace validation PASS.
- No system services, paid cloud or costly frontend bundle invoked;
  changes were developed on an isolated sparse Git worktree.

## Explicit open gates

Remaining non-dashboard hardcoded docs and inherited public help URLs
must be audited in subsequent bounded waves. This does not establish
an exhaustive app-wide egress inventory or independent live browser
egress proof. Full Django schema, SDK-to-queue-to-ClickHouse-to-dashboard
readback, production frontend bundle, full typecheck, OAuth and
multi-tenant isolation, and full E2E remain **NOT QUALIFIED**.
Release is **NO-GO**. Issues #24 and #82 remain OPEN.

TheHalfMoon/Flind stays PRIVATE. Inherited GitHub Actions remain
disabled. No deployment, publication, paid provider, or deletion of
required legal attribution.
