# Wave 81 — First-party Web Analytics operational help

## Why this wave

The Web Analytics health checks and Page Performance screens contained
hard-coded links to inherited vendor documentation. Some old UI
buttons would still render even if the intended Flind URL was missing.
These live operational actions could silently redirect Flind users to
an unrelated cloud service or present inert calls to action.

## Changes

Five focused source modules now use the existing explicitly configured,
same-owner HTTPS Flind documentation contract:

- **Health checks:** installation/capture, pageleave/bounce, scroll
  depth, session ID, reverse proxy, path cleaning and web-vitals.
  The real health issue detector, severity, internal domain settings
  and health IDs are unmodified. Installation/session-ID actions are
  omitted without a valid configured destination; internal settings
  actions remain available. The diagnostic copy uses Flind branding.
- **Page Performance:** server-log setup guide and channel attribution;
  no automatic vendor-site fallback; disabled guide controls are
  omitted and explanatory text remains.
- **Google Search Console breakdown:** only displays its external setup
  call to action if the Flind-owned documentation URL is valid.
- **Web Analytics filter bar:** online-user-count FAQ tooltip uses
  validated Flind URL and a separately validated section anchor.
- **Recordings tile:** an unconfigured recordings guide removes both
  the button label and the URL, avoiding an inert button.

All emitted deep URLs are derived from the operator's configured Flind
docs origin; no external host was invented. Existing API names,
database schema, ingest paths, public SDK compatibility identifiers
and legally required LICENSE/NOTICE attribution are untouched.

## Real evidence — 2026-10-25

- **6/6** standalone Node24/TypeScript tests PASS: no inherited docs
  URL within these five modules, correct TS/TSX parse and fail-closed
  optional buttons/actions; no unconfigured fallback.
- **76/76** targeted actual frontend Jest tests PASS in four suites:
  PagePerformance query logic, Web Analytics filter logic, Flind docs
  URL validation and FlindDocsLink DOM fallback.
- oxfmt format and Git whitespace guard PASS.
- Exact local Node.js 24 and pinned pnpm 11 were used in a separate
  sparse worktree; no expensive production frontend build was invoked.

## Explicit limits

This is not a full application-wide link or network-egress audit;
more external documentation links exist in other analytics scenes.
The full production frontend build, comprehensive TypeScript check,
browser E2E, full Django schema, real SDK→queue→ClickHouse→dashboard,
and OAuth/tenant isolation remain **NOT QUALIFIED**. Flind release
status remains NO-GO; identity/egress Issue #24 and release Issue #82
stay open. Repo stays private, inherited GitHub Actions disabled,
no publication, deployments or paid providers.
