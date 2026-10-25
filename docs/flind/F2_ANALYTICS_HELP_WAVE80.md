# Wave 80 — First-party help in analytics query surfaces

## Problem and scope

Eight active query/analytics screens contained nine hard-coded help
destinations under the inherited vendor's public documentation domain.
For a private, operator-owned Flind deployment, those are incorrect
default egress destinations.

Wave 80 moves these nine user-facing help controls to the validated,
operator-configured Flind docs URL contract implemented and tested in
Waves 78–79. It changes no data-source requests, analytics query
semantics, SDK API identifiers, legal source attribution or product
feature behavior.

## Migrated surfaces

- Web Vitals: explicit optional first-party docs link with section anchor.
- Web Overview: optional reverse-proxy warning link.
- InsightViz Session Analysis Warning: plain unlinked explanatory text
  when Flind docs are not configured.
- InsightViz Editor Filters: optional funnel graph-type tooltip link
  and validated attribution-types deep link.
- HogQL Query Editor: optional local help text/Flind Data Warehouse docs.
- Trends Series: optional filter-help link.
- Data Table: optional distinct-ID/person-profile tooltip docs.
- Web Analytics Session Attribution Explorer: first-party channel-type
  help, leaving unrelated local links untouched.

Static docs paths and section anchors are validated and appended to
the same canonical operator-owned HTTPS docs origin. Without a Flind
docs configuration, no inherited donor-host link appears; UI warning
text or tooltip titles remain visible.

## Executed validation — October 25, 2026

- **76/76 real frontend Jest tests PASS** across five suites:
  SessionAnalysisWarning React DOM fallback, Flind first-party URL
  validation, FlindDocsLink React DOM fallback, EditorFilters
  behavior, DataTable rendering behavior.
- **4/4 Node + pinned TypeScript syntax/ownership tests PASS**:
  exactly nine target help-control references, no inherited docs URL
  in all eight migrated files, valid TS/TSX parse, validated optional
  destinations without vendor fallback.
- Oxfmt all ten changed source/test files PASS, Git whitespace
  check PASS.
- The full app bundle, full typecheck, exhaustive egress scan,
  independent browser traffic verification, full Django schema,
  SDK-to-ClickHouse/dashboard E2E, OAuth/tenant checks and release
  remain **NOT QUALIFIED**.

## Operational constraints

No new domain invented or registered, no build/deployment, no paid
service, no changes to shared database or system Node. Work uses an
isolated Git worktree and exact local Node 24 + pnpm 11.
Preserve repository privacy, disabled inherited Actions and required
legal source attribution. Issue #24 stays open until application-wide
audit and independent browser egress qualification are completed.
