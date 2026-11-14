# Flind engineering status

The durable record of where Flind stands. Each milestone lists what changed, the PR and merge commit, the evidence
(CI runs on the exact merged commit), legal and security notes, and what is next. **Verified** means shown by a CI
run or test result on that commit; anything else is marked as planned or unverified.

Last updated: 2026-11-14 (current release-gate snapshot; historical sections below).

## Current release-gate snapshot (2026-11-14; reviewed against main `7764ce54765842521b16ca8dec6814ed26772dc8`)

This snapshot supersedes older open-PR and release-readiness statements below. It records a **source/PR inspection**, not newly completed CI or a release qualification.

- Open **draft** PRs at inspection: [#93](https://github.com/TheHalfMoon/Flind/pull/93) (quarantine inherited publishers), [#94](https://github.com/TheHalfMoon/Flind/pull/94) (remove Docker Hub credentials from agent-skills CI), [#95](https://github.com/TheHalfMoon/Flind/pull/95) (stdlib regression guard, deliberately red until credential remediation), and [#96](https://github.com/TheHalfMoon/Flind/pull/96) (metrics-agent test-only workflow). These changes are **not on main**. Do not merge without exact-head CI, code review, and conflict/concurrency inspection.
- On inspected `main`, `.github/workflows/ci-agent-skills.yml` still contains donor `DOCKERHUB_TOKEN`/login and `GH_APP_POSTHOG_*` token minting. PR #94 removes only the former. PR #95's guard is not yet wired into an enforced workflow. A condition restricting one token to the donor repository does not remove its dormant source path.
- PR #96 proposes replacing inherited metrics-agent image/chart publishing with tests on GitHub-hosted `ubuntu-24.04`. At inspection, no PR-triggered workflow runs were returned for its head `59347353d4ab2cafc39510223893cbc437689996`; **not qualified**. Verify Helm availability, render and integration smoke, and non-publishing Docker build validation before merge.
- **Unresolved:** other active CI/CD credentials and donor distribution paths, private SDK host/egress and artifact independence, broad cross-tenant security, real-data upgrade and cross-service restore, reproducible zero-cost installation/performance, owned HTTPS origins and legal pages, complete branding, and iOS/Android registration, signing, simulator/device and OAuth/push QA. Prior scoped CI successes do not establish these release gates.
- **NO-GO**: no tag, GitHub Release, deployment, SDK publication, app-store submission, paid infrastructure, or binary distribution until explicit founder `GREEN LIGHT FLIND`. Keep donor licenses/attribution and synthetic-only public CI fixtures.

## Current integration checkpoint (2026-11-13; main `42ceee9173bd7bf68f74aea30b4cd70f3037c018`)

This section supersedes the older release-gate table and dated PR descriptions below wherever they conflict. Older entries are retained as historical engineering evidence, **not** current release readiness.

- PRs #47–#63 have been reported merged in the repository's recent integration sequence. The recent stages cover mobile-owned OAuth/legal/telemetry/status, provisional native identity, desktop/web OAuth no-redirect, desktop telemetry, Node ingestion-host restrictions, and React SDK auto-init restrictions. Do not infer production E2E or public SDK readiness from these scoped changes.
- PR #64 stages private `@flind/core`; #65 stages its private Node dependency; #66 stages private `@flind/types`. PR #67 merged at `3f4581b91f816d0e02e28f73da4d8d011bb46958`, linking the local types package to core without changing compiled CJS/ESM runtime. All five exact-head checks (`core`, `node`, `types`, `ratchet`, database `migrate`) passed on PR #67. These are private staging checks, **not** a public SDK, end-to-end ingestion, or publication qualification.
- PR #70 merged at `97c7b1e15176df235de996be7621d6c31b81cbc3`: a synthetic, ephemeral PostgreSQL custom-format backup and separate restore passed real CI. PR #71 merged at `52c862427b9c13f45b09fa4febc5ceaaec628013`: health help links are now first-party-or-hidden, with Jest/TypeScript/ratchet/migration checks green. PR #72 merged at `09d70754a09b35ff0956d89d19bb5312c6f28ec0`: real PostgreSQL and ClickHouse migrations preserved two synthetic tenant rows across idempotent rerun. None establishes a production cross-service recovery or upgrade-from-prior-release qualification.
- PR #75 merged at `b1ef5b02ca5c27d149712993881724f8b98dd4bb`: real-service CI tested that the migration canary detects modified PostgreSQL and deleted ClickHouse synthetic tenant rows, then verifies repaired parity. PR #74 merged at `2e7c49e272123e7184c20c56188fae73388ade0f`: actual ClickHouse `FORMAT Native` export/import, negative-control tampering and re-import passed on a disposable table. Neither is a full production database backup, verified RPO/RTO or cross-service recovery.
- PR #68 merged at `ff9bc08ffb9a198691aeaadf159995fca8a7b255`: exact-head opt-in full-service run `43374359228` **passed** actual Node and browser SDK capture -> Kafka -> ClickHouse queries and independent-organization negative controls after an earlier Node-host routing failure. Ordinary Playwright, migration, contract, rename and validation checks also passed. This proves the scoped ephemeral E2E, **not** production collectors or broad SDK acceptance. PR #73 merged at `6fed1334c167bb122fc977263b86938fa3488d75`: integration help links now use optional first-party docs and the inherited Slack marketing banner was removed, with exact-head frontend Jest/TypeScript and migrations green. PR #76 merged at `f98f7673ba363d638778090f66aad6eb238e7e44`: real Caddy E2E now proves both named loopback hosts work with its locally restricted port; production proxy settings are unchanged.
- PR #77 merged at `f06d87c63818fb739b1b633576b4d92d571feb89`: the transitional **public compatibility** Node SDK onboarding snippet now instantiates an actually exported API; its five checks passed. No publicly released `@flind/node` package was claimed. PR #78 merged at `2b2f5248c651e7d44e1a3f51e7bb5942d4736b4a`: React Native onboarding now has optional owned documentation and privacy-first copyable replay sample defaults; all five exact-head checks passed. The optional sample defaults are **not** an enforcement change to deployed SDKs.
- PR #79 merged at `ea569777415d8b4968cdb223c254e650b775fb5c`: real SeaweedFS 4.29 S3 API test in run `43382699204` exported two distinct synthetic tenant objects, deleted them, restored byte-for-byte, detected deliberate tampering, and re-restored successfully, with no archive upload. This qualifies a scoped **logical object recovery smoke**, not complete or production object-store backup/disaster recovery.
- PR #81 merged at `cc18c43671cf7e3dded9ab5e2471f7989e37defb`: the source-map onboarding wizard no longer offers the unqualified external CLI installer, authentication/upload commands or automatic Next.js/Nuxt/iOS symbol-uploader cards, while retaining non-upload alternatives and skip; Jest, TypeScript, migration, rename and contract checks passed. Old source-map uploader files and the CLI still exist but are not qualified for Flind distribution.
- PR #82 merged at `2dca3f1b198ac47c5f84e123807d9eb637b53871`: native Rust CLI `posthog_rs` usage/error reporter calls fail closed by default without independently owned diagnostic destination, with three source security tests and exact-head CI green. WSL Ubuntu full Cargo all-targets suite passed **357/357** with original Git fixtures (272 Rust library + 85 integration tests). This does **not** prove that the separate embedded Node API bundle cannot send analytics, or qualify native installer/CLI data-upload egress.
- PR #80 merged at `42ceee9173bd7bf68f74aea30b4cd70f3037c018`: all **93** SDK catalog help destinations are now optional first-party Flind docs URLs validated against the operator-owned HTTPS host, with a render-boundary guard rejecting unsafe direct overrides; the default without configured owned docs is explanatory text, never a donor link. The first Jest failure was a stale label assertion; the corrected exact-head **five CI checks passed** (Jest, TypeScript, migration, ratchet, contract) before merge. Actual publication of deep Flind docs pages remains separate. This status-ledger PR #69 is the last open draft at this checkpoint. None of these changes qualifies a public Flind SDK, iOS native application, or production release.
- The prior ledger's claims that SDK ingestion E2E was entirely unverified, or that mobile had not been built in CI, are **historical** and no longer accurate as blanket statements: a scoped Node-to-capture-to-ClickHouse cross-tenant test and scoped Android compilation were reported in merged PRs. Production deployment, broad SDK matrix and native device QA remain unverified.
- Release blockers: independently owned/published browser, Node, React Native, Python, Rust and mobile SDKs with broader real-host and real-device ingestion/egress coverage beyond the now-passing scoped Node E2E; **upgrade from an earlier released version** with real application data; complete PostgreSQL/ClickHouse/object storage/Kafka/Redis backup and restore with cross-service consistency, RPO/RTO and disaster recovery; tenant-boundary auth/security campaign; reproducible independent installation, resource requirements and performance; actual owned HTTPS service origins, policy URLs and docs pages; registered mobile bundle IDs/signing, iOS simulators and real-device OAuth/push; complete frontend branding/UX and end-to-end user journeys.
- **High-risk unqualified source-map CLI (UI now safely withheld):** #81 removed the inherited installer/login/upload commands from the active source-map wizard, and #82 disables Rust diagnostic reporters. However the copied `cli/` crate/package, its upstream release/install/update flow, inactive source-map example components, embedded Node API proxy and unqualified outgoing file-upload routing **still exist**. Independently rebrand and qualify builds, installer origins, signed/checksummed release artifacts, complete native + embedded Node network egress, explicit first-party HTTPS destination, project/tenant permissions and synthetic negative upload controls before re-enabling user symbol uploads. Other external navigation outside #80's SDK selector remains a separate branding/security task. Preserve all legally required third-party source NOTICE without using it as Flind marketing.
- Legal: retain required donor licenses, copyright notices and provenance, including private staged SDK packages. Do not rewrite signed fixtures.
- **NO-GO for release:** no tag, GitHub Release, deployment, SDK publication, app-store submission or binary distribution without the founder's explicit `GREEN LIGHT FLIND`. No paid infrastructure, real customer data or secrets in engineering tests.


## Cross-organization personal API-key authorization: scoped evidence (2026-11-13)

- **Merged [PR #83](https://github.com/TheHalfMoon/Flind/pull/83)** at `d19ee4789527675934e5dcd834a7367e71a535f8` (qualified head `75623997d02fff48fe12a7090dca65a931bab5f7`) adds bidirectional negative personal-key probes for real capture, Node SDK and browser SDK ingestion. A foreign organization's valid personal key must receive 401/403/404 on the target team's HogQL query endpoint; a 2xx empty result and 5xx both fail the test. An additional no-redirect hardening is being independently qualified in draft #86.
- **Verified directly from GitHub Actions job logs on 2026-11-13:** [E2E run 43408588563](https://github.com/TheHalfMoon/Flind/actions/runs/43408588563), job `131829009448`, checked out exact head `75623997d02fff48fe12a7090dca65a931bab5f7` with `FLIND_INGESTION_SMOKE=true`. Real-service setup, migrations, capture/ingestion startup and Chromium succeeded; **4 general journeys and 3 opt-in ingestion suites passed** (browser SDK, direct Rust capture and Node SDK). [Authorization contract run 43408588238](https://github.com/TheHalfMoon/Flind/actions/runs/43408588238), job `131829001634`, also checked out that exact SHA and succeeded. Direct job retrieval and logs independently establish these outcomes. The successful run was inspected before PR #83's merge. A separate follow-up [PR #86](https://github.com/TheHalfMoon/Flind/pull/86) prevents a redirected foreign-key request from being misinterpreted as a denial; its own full-service test is independently required, not covered by #83's run.
- [PR #84](https://github.com/TheHalfMoon/Flind/pull/84) was merged at `cf96547011384c1733fc2d602a9a88382b27bf9a`: its Node API proxy now refuses unqualified or conflicting host aliases before passing credentials into the embedded Node child. WSL Cargo all-targets tests **363/363** and 13 Python contract tests passed locally, plus exact-head GitHub CI. Complete embedded Node network egress and public installer/update origin remain unqualified.
- [PR #87](https://github.com/TheHalfMoon/Flind/pull/87) is an independent draft to bundle the previously remote SDK selector images locally with byte hashes, provenance and all 93 SDK entries preserved. Its exact-head frontend CI is required before merge; it is not part of PR #83's ingestion evidence.
- Authorization evidence covers **only** the tested real-time query endpoint, not all export, upload, administrative, role, or cross-tenant routes. No production release gate is cleared. **NO-GO** and `GREEN LIGHT FLIND` restrictions remain unchanged.

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

### 2026-11-12 Node wire guard DNS hardening (PR #41)
- At f1a993f7522e, GitHub reported all three attached checks successful: wire-parity, rename ratchet, and runtime migrations. This does not substitute for independent review or additional applicable CI.
- Removed hostname-based `localhost` allowance and implicit default-host allowance from the Node TCP guard. Only literal 127.0.0.1 or ::1 at the allocated test-server port may pass. Added negative controls for `localhost` and unspecified host to prevent DNS/hosts-file redirection.
- Windows Node 24 `node --check` and `git diff --check` passed; Node 26 CI must run at the new exact SHA. No merge or release authorized.

### 2026-11-12: PR #45 contact-sales behavior coverage
- Added a Kea logic regression test for Cloud preflight with no eligible billing plans: the contact-sales gate must expose no destination and must provide the Flind unconfigured-sales disabled reason. Extended the donor CTA guard to require this test.
- Windows Node guard: 3 passed, 0 failed; git diff --check passed. Jest/TypeScript not run locally, and exact-head CI plus independent review are required before merge.
- PR #45 remains draft. No public release or deployment authorized.

### 2026-11-12: PR #45 disabled CTA button wiring guard
- Added a static negative-regression guard for both PayGateButton and PayGateIcon: both must pass the Kea disabled reason into LemonButton and must not invent a fallback destination when ctaLink is undefined.
- Windows node --test frontend/bin/flind-donor-cta-isolation.test.mjs: 4 passed, 0 failed. git diff --check passed. This source guard does not replace Jest/TypeScript or browser E2E.
- Earlier exact-head GitHub CTA guard, rename ratchet and runtime migrations passed on 566993def; requalification is required after this change. PR remains draft; no deployment or release.
