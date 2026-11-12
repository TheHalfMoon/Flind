# Flind engineering status

The durable record of where Flind stands. Each milestone lists what changed, the PR and merge commit, the evidence
(CI runs on the exact merged commit), legal and security notes, and what is next. **Verified** means shown by a CI
run or test result on that commit; anything else is marked as planned or unverified.

Last updated: 2026-11-12.

## Project and experiment documentation isolation (2026-11-12)

- **Branch:** `flind-ci/project-experiment-docs-isolation-20261112`, based on main `48def4f74f922ad3a90b4d695d253171bb78773c` at creation. Independent of merged PR #29, #32 and #33 changes. No SDK or runtime data schema changes.
- **Changes:** project creation guidance no longer links to unowned donor documentation while preserving project-isolation and conversion advice; the experiment results 'How to read' tooltip remains a local help trigger, rather than navigating to an unowned donor site. Both features retain their existing actions and explanatory content.
- **Verification:** exact-branch files fetched into a temporary Windows directory; `python tools/flind/test_project_experiment_docs_isolation.py -v` passed **2/2** assertions. This is source-level verification, not React runtime or browser E2E. Temporary files were removed. The brand audit, frontend, E2E, runtime migrations and rename ratchet passed on `579a0c0cc`; this merge commit still requires renewed CI.
- **Required before merge:** fresh exact-head CI brand audit, frontend typecheck/Jest and browser E2E where applicable; independent review, branch protection and source attribution preserved. No release or deployment.

## Toolbar documentation isolation (2026-11-12)

- **PR #29:** removes three inherited documentation links from Chrome extension menus and fragile-selector warnings; local metrics navigation, reload, screenshot/PII/debug controls, and inline selector guidance remain.
- **Prior exact-head CI** on `70bce0470`: frontend, E2E, brand audit, rename ratchet and runtime migrations all passed. This merge commit still requires fresh CI qualification.
- **No release** is authorized; other hosted donor links remain separate follow-ups.


## Activity UI rebrand checkpoint (2026-11-12)

- **PR #30 merged** into `main` as `76f95d7d426e9efde331fd30849b8add7747c619` after five CI paths passed on exact PR head `ea187e5d9ac033f24442e3a93e206d729c72f0d0`.
- It removes inherited documentation links from Persons/Cohorts tooltips and Event Details and donor CLI promotion from Live Events. The event feed and navigation remain.
- No Flind documentation endpoint or CLI is invented.

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

### 2026-11-12: Error tracking UI documentation isolation (draft)
- Scoped change: remove inherited PostHog documentation destinations from fetch failure banner, empty stack trace help, and fingerprint tooltip. Keep local explanations and fingerprint display behavior.
- Local verification: source diff reviewed and `git diff --check`; full Jest/TypeScript/Playwright and independent review remain required on the exact PR SHA.
- No deployment or release authorized. Do not merge without applicable green CI and review.

### 2026-11-12: Cyclotron template help isolation (draft)
- Removed the donor-hosted documentation link from the live destination template suggestion panel. Retained function suggestions, Hog/Liquid selection, and the third-party Liquid language reference.
- Added dependency-free regression coverage to the existing Brand Audit suite. One focused test passed locally; complete CI and independent review are required before merge.
- No deployment or public release authorized.

### 2026-11-12: Node SDK ingestion path negative-control (PR #41 follow-up)
- Added an independent /batch/ path assertion to the local HTTP wire validator and a synthetic negative-control packet at /unexpected/ that must be rejected. This supplements pinned SDK parity; it does not prove global outbound network isolation.
- Windows Node 24 syntax check and git diff --check passed; full Node 26 workflow and independent review remain required before merging.
- No public Flind release or deployment authorized.

### 2026-11-12: Node SDK outbound socket guard (PR #41 follow-up)
- Scoped Node wire test guard intercepts Node TCP socket connects during synthetic SDK capture and permits only the ephemeral 127.0.0.1 HTTP test-server port. Negative controls reject an external hostname and a wrong loopback port before dialing. The original Socket.connect is restored in finally.
- This is a process-level Node socket guard, not OS-level network isolation; independent review must assess alternate transports and DNS behavior. Node 26 CI is the authoritative runtime qualification; Windows Node 24 syntax and git diff checks alone do not prove SDK E2E success.
- No release, deployment, or merge until all applicable exact-SHA checks and review complete.

### 2026-11-12: Node SDK socket normalization repair (PR #41)
- Exact SHA 698ecafc9 CI wire-parity failed: both positive captures raised PostHogFetchNetworkError because the guard rejected Node net.createConnection normalized [options, callback] arguments. Negative controls passed; rename and migration checks passed.
- Updated the guard to unwrap normalized connection arguments before validating host and ephemeral loopback port. Added negative controls for normalized external-host and incorrect-port destinations. This is a narrow test-harness fix, not a relaxation of permitted network destinations.
- Windows Node 24 syntax and git diff --check passed; Node 26 CI and independent review are still required. No merge or public release.

### 2026-11-12 Node wire capture strictness (PR #41)
- At df6881851, GitHub reported wire-parity, rename ratchet and runtime migrations successful. The next commit strengthens the validator to reject any extra local route or HTTP method even if a valid batch is also present; includes negative-control tests.
- Local evidence: node --check and git diff --check passed on Windows. Full Node 26 SDK execution and exact-head CI remain required before merge. No deployment authorized.
