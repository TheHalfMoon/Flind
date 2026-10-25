# Wave 62 — First-party identity for active Flind UI surfaces

## Scope and behavior

This is a small, explicit set of **visible product copy** updates, not a
global source-code rename or legal attribution rewrite.

- System-created annotations display a **Flind** badge.
- Core taxonomy definitions display **Flind** with a neutral badge icon
  instead of an inherited vendor logomark. The tooltip describes a
  built-in definition without claiming a deployed public documentation site.
- The exception UI reports "captured by Flind" when there is no Sentry URL.
- Audit logs identify system activity as **Flind** and impersonated actions
  as **Support (as …)**. They continue hiding the impersonated member's
  email from the actor field. Historical actor identities are not rewritten
  in stored events.
- The group-analytics help link no longer points at the inherited
  vendor. It renders only when `flindPublicUrl('docs')` returns an
  explicit, HTTPS, first-party URL owned by the operator; otherwise the
  link is absent and the core "Unique groups" explanation remains.

Technical wire formats, required notices, fixtures, package boundaries and
persisted schema labels are **not** globally renamed by this wave.

## Executed evidence — October 25, 2026

- Standalone source contract tests: **6/6 PASS**.
- Parsed all six edited TS/TSX component/test files with Babel's
  TypeScript+JSX parser: **6/6 PASS**.
- `git diff --check`: **PASS**.
- Activity-log frontend regression expectation is updated and an additional
  behavior test covers an impersonated actor's name and hidden email.
- Complete frontend typecheck, component browser tests, native/mobile builds
  and production bundle identity scans **were not executed** by this
  limited environment. The remaining inherited brand/egress gates are
  still open (#5, #24, #82).

## Operational boundaries

Keep TheHalfMoon/Flind private, repository Actions disabled, no deployment
or public publication, no paid services, and all mandatory attribution.
This isolated frontend change is not evidence of product release readiness.
