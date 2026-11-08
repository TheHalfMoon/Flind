# Flind brand audit — 2026-11-08

Source: `.github/workflows/flind-brand-audit.yml`, run 42434903452, main `e8171fc`.
Counts the literal `PostHog` (what users read). Test files, snapshots and node_modules are excluded.

## Size of the rebrand

| Scope | Lines | Files |
| --- | ---: | ---: |
| Everything scanned (`frontend/src`, `products`, templates, settings) | 21,358 | 4,834 |
| After excluding fixtures, mocks, evals, generated code and markdown | 10,189 | 3,950 |
| `frontend/src` (core UI) | 2,200 | 725 |
| Email templates (`posthog/templates/email`) | 63 | 35 |
| All server templates (`posthog/` + `ee/templates`) | — | 43 |
| Runtime messages (`posthog/settings`) | 37 | — |

The single largest file is a test fixture (`products/engineering_analytics/fixtures/github_workflow_runs.json`, 6,756 lines). Fixtures are not user-facing and are lowest priority.

## Product areas by occurrences (all files)

engineering_analytics 7,169 · frontend/src 2,694 · warehouse_sources 2,143 · desktop 1,417 · signals 1,048 · review_hog 692 · slack_app 678 · tasks 666 · posthog_ai 531 · workflows 222 · data_warehouse 213 · ai_observability 173 · customer_analytics 159 · canvas 153 · experiments 144 · error_tracking 141

## Order of work (each one a reviewable private PR, qualified in CI)

1. **App shell**: browser title, favicon, logo components, meta tags, one central product-name constant, and removal of `posthog-logo.*` / `posthog-icon.svg` from `frontend/public`.
2. **Emails and server templates** (43 files): every message a user receives.
3. **Runtime messages**: settings warnings (for example "PostHog is running in DEVELOPMENT MODE!"), installer and CLI output, error text.
4. **Core UI** (`frontend/src`, 725 files): navigation, onboarding, settings, empty states. Links to posthog.com docs need a Flind docs target; this needs an owner decision.
5. **Product modules** in order of how central they are to Flind's analytics journeys (insights, dashboards, flags, experiments, replay before peripheral products).
6. **Guardrail**: a CI check that fails when new user-facing `PostHog` text appears outside an allowlist (licence notices, compatibility-critical identifiers such as `posthog-js`, and SDK wire formats).

## Kept on purpose

Copyright and licence notices (`LICENSE`, `ee/LICENSE`), Python package and module paths (`posthog.*`), historical migrations, and SDK and wire-protocol identifiers are compatibility-critical. They stay, and the guardrail allowlist will document each one.
