# Wave 79 — First-party Support settings help and deep-link sections

## Scope

The active Support Settings views for Direct API, General, Widget,
Notifications/Workflows, Slack and Microsoft Teams still opened nine
hard-coded donor documentation destinations. Those destinations have
been converted to reusable first-party help controls.

This is a user-visible URL/branding fix, **not** a change to Support
API endpoints, identity-verification cryptography, Slack/Teams bot
registration, Microsoft tenant application packages or SDK names.
Those external integration names need their own qualified rebranding
and must not be silently changed by a documentation-only wave.

## Owned documentation contract

`FlindDocsLink` shows a link only when a verified operator-configured
`VITE_FLIND_WEBSITE_HOST` + `VITE_FLIND_DOCS_URL` satisfies the
existing exact same-origin HTTPS checks. Otherwise, it renders its
help text without an anchor or clickable external destination.

For widget and identity-verification docs, the new
`flindDocsSectionUrl(path, section)` separately validates the
documentation path and section slug, then adds the fragment only
on the Flind first-party origin. This rejects arbitrary # fragments,
queries, URL credential tricks and non-owned domains.

The nine converted help links are distributed across:
- Direct API (1)
- General settings / identity verification (2)
- Widget (2)
- Workflows/Notifications (1)
- Teams (2)
- Slack (1)

The underlying `posthog.conversations` JavaScript API and the currently
registered `SupportHog` integration names remain unchanged for SDK
and provider compatibility. Their user-facing identity is tracked
under the existing branding/release issues; changing an unqualified
third-party integration ID or API namespace here would cause breakage.

## Executed evidence — October 25, 2026

- **47/47** real Jest tests for first-party Flind docs links,
  including section anchors, unconfigured docs and unsafe inputs.
- **2/2** real Jest DOM checks: `FlindDocsLink` emits readable
  unlinked text when docs are absent, for both ordinary and deep links.
- **14/14** existing ProductEmptyState behavior tests PASS.
- Thus **63/63 targeted Jest checks PASS** across three suites.
- **3/3** Node + pinned TypeScript source tests PASS: all nine live
  Support settings help controls use `FlindDocsLink`, no inherited
  hard-coded docs destinations remain in these six pages, and the
  public SDK/provider integration identifiers are left intact.
- Source formatting and whitespace checks are required before merge.

## Remaining gates

This is a **bounded migration of six active settings sections**, not
a claim that every application link or network request has been audited.
Full browser egress, domain ownership/production verification, actual
OAuth/PKCE and external integration configuration, full frontend
production build, E2E, full Django migration graph and SDK-to-ClickHouse
end-to-end evidence remain outstanding.

Keep issue #24, broader branding issue #5 and release issue #82 OPEN.
Repository remains private with inherited GitHub Actions disabled,
no deployment, publication or paid providers, mandatory donor
LICENSE/NOTICE preserved.
