# Flind engineering status

The durable record of where Flind stands. Each milestone lists what changed, the PR and merge commit, the evidence
(CI runs on the exact merged commit), legal and security notes, and what is next. **Verified** means shown by a CI
run or test result on that commit; anything else is marked as planned or unverified.

Last updated: 2026-11-11.

## Current stage 3 checkpoint (2026-11-11)

- Rename PRs #20 (user-facing Flind copy), #21 (legacy legal-documents feature off), and #22 (`@flind/siphash`) have merged; `main` was verified at `66cc22360e50ce5835f834dbbaf091e8339cac5c` before this icons work.
- Next stage: local working branch `flind-ci/rename-03b-icons` prepares an `@flind/icons` workspace package and replaces inherited icon imports. This branch remains **unqualified** at this checkpoint, and must remain unmerged until lockfile, CI, branding, and runtime checks complete.
- **Founder rights representation:** on 2026-11-11 the founder explicitly stated they have full permission to take and rebrand the bundled third-party icon source and artwork for Flind. The permission documents have not been independently inspected or stored in this repository. Retain legally required original licensing and provenance; use **Flind** for active product-facing branding.
- Existing upstream brand and mascot packages remain separate follow-up tasks; no icon conversion alone means the complete application has been rebranded.

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
