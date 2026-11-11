# Flind engineering status

The durable record of where Flind stands. Each milestone lists what changed, the PR and merge commit, the evidence
(CI runs on the exact merged commit), legal and security notes, and what is next. **Verified** means shown by a CI
run or test result on that commit; anything else is marked as planned or unverified.

Last updated: 2026-11-11.


## Extension packaging qualification checkpoint (2026-11-12)

- Main remains `66cc22360e50ce5835f834dbbaf091e8339cac5c` at the start of this checkpoint; PR #23 (`ff40a2ea5929`) and security PR #24 (`002e558944e5`) remain open, with no deployment authorized.
- PR #25 Chrome extension package qualification run [43106498600](https://github.com/TheHalfMoon/Flind/actions/runs/43106498600) **FAILED** on `2fef2f23` at the actual extension build, despite the focused icon tests passing. The fresh CI runner did not contain `@flind/quill/dist/tokens.scoped.css` and `@flind/quill-primitives`, `@flind/quill-components`, `@flind/quill-blocks` dist JS outputs. This is a real build dependency failure, not an icon-test failure.
- Narrow CI repair `6be3c80d` adds the existing Quill workspace build before extension packaging and asserts expected generated files. GitHub run [43115192575](https://github.com/TheHalfMoon/Flind/actions/runs/43115192575) and manual run [43115204760](https://github.com/TheHalfMoon/Flind/actions/runs/43115204760) were **not completed at checkpoint**. Do not claim a package pass until the actual Chrome manifest, icon, archive and all applicable exact-head checks succeed.
- No merge, release, distribution, or deployment. PR #25 is stacked on #24; #23 remains an independent merge prerequisite for subsequent package/SDK work. Independent review and branch protection still apply.

## Live qualification checkpoint (2026-11-11, later run)

- **Main:** `66cc22360e50ce5835f834dbbaf091e8339cac5c` at the start of this checkpoint; no release or deployment authorized.
- **PR #23, icons:** draft head `ff40a2ea5929fe0330077de000acaac5fa2017a5`. Earlier lockfile repair was followed by a Playwright alias fix: `@flind/icons` now resolves to executable workspace code rather than `packages/icons/index.d.ts`. At inspection, 9/17 checks succeeded, 8 were still running; no failures reported yet. The separate Playwright real-service run `43087399986` remained in progress during database setup. **Not qualified and not merged.**
- **PR #24, toolbar origin isolation:** draft branch adds default-deny external messaging, explicit origin validation, tests for actual manifest-builder wiring, and rejection of trailing-dot DNS hostnames (including inherited donor domains). Local Windows `node --check` and `node --test`: **6 passed, 0 failed**, on the updated files. GitHub CI on the final PR head was still queued/running at inspection; packaging and browser runtime are **not yet verified**. **Not qualified and not merged.**
- **Next gate:** require all exact-head checks and real-service E2E to finish successfully before merging; then verify main. SDK ownership transfer and SDK-to-Flind ingestion E2E remain outstanding.
- **Legal:** founder reports permission to rebrand donor artwork and code; retain applicable copyright, licensing and provenance. Do not rewrite signed fixture data.
- **Release:** prohibited until explicit **GREEN LIGHT FLIND**.

## Release gates

| Gate | State |
| --- | --- |
| Required Flind CI green on `main` | Verified for each merged PR below (exact head commit). |
| Brand and attribution guards | Verified: `tools/flind/test_user_facing_brand.py` in the brand-audit workflow. |
| No PostHog-hosted runtime dependencies | Not verified. Known gaps: mobile app legal links, toolbar trusted PostHog hosts, `npx @posthog/wizard` onboarding. |
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

## In progress

- **#20, rename stage 2:** "PostHog" becomes "Flind" in user-facing text across 6,530 files. Includes the owner's SDK-label
  corrections (the inherited SDK is labelled as the PostHog SDK until stage 3 vendors it).
- **Legal-documents feature off:** the inherited BAA/DPA feature (contracts with PostHog Inc.) is switched off by
  `FLIND_LEGAL_DOCUMENTS_ENABLED` (default off) and removed from navigation. Stacked on #20.

## Next

1. Rename stage 3: vendor PostHog's SDKs and `@posthog/*` dependencies as `@flind/*`; verify event ingestion end to end.
2. Stage 4: the Python package. Stage 5: database tables (Postgres and ClickHouse) with fresh-install and upgrade tests.
   Stage 6: environment variables, services, images, crates, modules, paths.
3. Runtime independence audit (PostHog-hosted URLs, telemetry, redirects) and the release gates above.

## Open owner decisions

- Three commits on #20 are authored with a personal email address in this public repository. Rewriting them needs
  the owner's approval.
