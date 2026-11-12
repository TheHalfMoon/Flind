# Flind engineering status

The durable record of where Flind stands. Each milestone lists what changed, the PR and merge commit, the evidence
(CI runs on the exact merged commit), legal and security notes, and what is next. **Verified** means shown by a CI
run or test result on that commit; anything else is marked as planned or unverified.

Last updated: 2026-11-12.

## Stage 3 qualification checkpoint (2026-11-12)

- **Main:** PR #23 merged as `b9e66abbbec7581e073de1ba933e8f11eab4f1a2`. The `@flind/icons` workspace migration passed exact-head frontend, backend, upstream, E2E, brand-audit, rename-ratchet, and runtime-migration workflows; ESM and CommonJS React smoke tests also passed on Node 26.
- **PR #24, toolbar origin isolation:** this branch implements default-deny extension messaging, opt-in exact HTTPS origin validation, rejection of inherited hosts, and tests wired to the generated manifest builder. Its prior exact-head rename-ratchet and runtime-migrations jobs passed. This integration merge with main still requires renewed qualification.
- **PR #25, extension brand icon:** stacked on #24. The initial actual extension build failed on missing Quill outputs (run 43106498600); its subsequent Quill prerequisite repair passed exact-head rename-ratchet, runtime-migrations, and toolbar extension qualification on `0b802897fa7e64431ead1f9bfe71003383b70850`. This integration merge with updated #24 requires renewed CI qualification.
- **Remaining release gates:** SDK ownership and end-to-end Flind ingestion, comprehensive deployment/security/upgrade qualification, and removal of remaining hosted donor dependencies are unverified.
- **Rights/provenance:** founder reports permission to use and rebrand donor artwork and code. The underlying permission documents have not been independently inspected; preserve required licenses and notices, and do not alter signed fixtures.
- **Publication:** prohibited until explicit **GREEN LIGHT FLIND**. No deployment or release authorized.

## Release gates

| Gate | State |
| --- | --- |
| Required Flind CI green on `main` | Verified for each merged PR below (exact head commit). |
| Brand and attribution guards | Verified: `tools/flind/test_user_facing_brand.py` in the brand-audit workflow. |
| No PostHog-hosted runtime dependencies | Not verified. Known gaps: mobile app legal links and `npx @posthog/wizard` onboarding; toolbar origin restrictions are in PR #24 and still require complete integration qualification. |
| Core user journeys | Partly verified: 4 Playwright journeys (`playwright/e2e/flind-brand-journeys.spec.ts`). Full journey set not built. |
| SDK event ingestion end to end | Not verified. |
| Fresh deployment | Not verified as a release artifact. CI brings up the dev stack only. |
| Upgrade migrations preserve data | Partly verified: real-service migration runs (Django and ClickHouse, idempotent re-run). No upgrade-with-data test yet. |
| Authentication and tenant isolation tests | Partly verified: upstream security suites run in `flind-upstream-tests.yml`. No dedicated Flind security campaign yet. |
| Desktop and mobile | Out of scope for the first release until qualified. Not built in CI. |
| Backup and recovery | Not verified. |
| API and developer docs match behaviour | Not verified. |
| Performance benchmarks | Not measured. |
| Reproducible deployment artifacts | Not built. |
| Release checklist | Not started. Publication stays on hold until the owner's GREEN LIGHT FLIND. |

## Milestones

| PR | Merge commit | What |
| --- | --- | --- |
| #1 | `33256b3` | Real-service migration qualification: ClickHouse 346/346, Django, idempotent re-run. |
| #2–#8 | `4589372`…`ff0c09e` | First rebrand: app shell, emails, API errors, core UI, model help text (migration), legal-copy corrections. |
| #9 | `a5bbb0f` | Source registry of the PostHog GitHub organisation (415 repositories). |
| #10 | `1cfe1ce` | Upstream cutoff pinned at `4efa693e9aec`; file-level delta recorded. |
| #11–#17 | `de44833`…`2ce3b1a` | 25 upstream security fixes, each with its upstream tests (`flind/upstream-sync/security-fixes.md`). |
| #18 | `35de3ed` | Upstream merged to the cutoff: 912 conflicts, backports replaced by upstream's originals, 10 new upstream workflows left out (`flind/upstream-sync/merge-4efa693e9aec.md`). |
| #19 | `f1728a0` | Full rename stage 1: plan, inventory and ratchet (`flind/rename/`). |
| #20 | `d9a845f` | Rename stage 2 user-visible copy and follow-up regression fixes. |
| #21 | `ce23b45` | Disable inherited legal agreements by default and add a status ledger. |
| #22 | `66cc223` | Vendor SipHash as `@flind/siphash`. |
| #23 | `b9e66ab` | Vendor icon bundle as `@flind/icons`; React and CI qualification on exact PR head. |

## In progress

- **#24:** qualify extension origin default-deny integration against main after #23.
- **#25:** qualify the corrected Chrome extension icon and packaging branch on top of #24.
- **Remaining rename stages:** SDKs, Python packages, database tables and service identifiers remain pending.

## Next

1. Rename stage 3: vendor PostHog's SDKs and `@posthog/*` dependencies as `@flind/*`; verify event ingestion end to end.
2. Stage 4: the Python package. Stage 5: database tables (Postgres and ClickHouse) with fresh-install and upgrade tests.
   Stage 6: environment variables, services, images, crates, modules, paths.
3. Runtime independence audit (PostHog-hosted URLs, telemetry, redirects) and the release gates above.

## Open owner decisions

- Three commits on #20 are authored with a personal email address in this public repository. Rewriting them needs
  the owner's approval.
