# Wave 40 — Welcome navigation and startup support do not route to inherited vendor

## Corrected product links

The Welcome API included four externally hosted documentation destinations
belonging to the source project's vendor, although the suggested next step
itself was a valid internal project route. Remove those optional docs_href
fields instead of inventing unverified Flind docs URLs. The Welcome API's
serializer already makes docs_href optional and the UI card conditionally
renders that link.

Desktop's stalled boot shell still said PostHog and offered a support button
that opened the source vendor's Discord. Correct the product name and
accessibility label, keep Retry, and show that operator support has not yet
been configured. No inert "get support" button or invented destination.

## Additional dependency integrity fix

During native Desktop UI Vitest qualification, pnpm failed with npm 404
because an earlier rebrand had changed two *published external* packages
into nonexistent registry names: @flind/quill and @flind/quill-charts.
The source donor's package.json already proved the original published
registry packages were the source vendor’s published Quill and Quill Charts artifacts,
both at version 0.3.0-beta.29.

The actual public npm versions and sha512 integrity strings were checked.
Use npm aliases in Flind's workspace catalog and UI manifest so hundreds
of existing @flind/... imports retain their internal identity while npm
fetches the correctly named, legally attributed third-party packages.

The pnpm lock was surgically corrected rather than accepting unrelated
hoisted-order churn. Its frozen lockfile supply-chain verification passed
for 3,041 entries. Frozen no-script UI install now succeeds.

## Evidence

- Execute the actual Welcome API helper from its Python AST, exercising
  role-filtered project routes and the no-activity home fallback; verify
  that no returned link navigates to unrelated vendor documentation.
- Original AppLoadingScreen Vitest: **5/5 PASS** after frozen install.
- Full @flind/ui TypeScript tsc --noEmit: **PASS**.
- Real frozen pnpm --ignore-scripts install and lockfile verification: PASS.
- Additional source regressions guard actual published registry aliases.
- Full Flind Python source regression suite: **309/309 PASS**.
- Narrow, version-bound exception to the old identity gate only for the
  two attributed npm aliases in three dependency metadata files.
- No Django/Postgres/ClickHouse service E2E is implied by these checks.

## Scope and release gates

Other Desktop support and privacy links in shared EXTERNAL_LINKS remain
under audit and are NOT qualified by this change. The application still
requires reviewed first-party documentation, support and privacy pages.
Actual backend/DB and native UI E2E remain unqualified. Keep the repo
private, inherited Actions off, third-party legal attribution and no
publication/deployment.
