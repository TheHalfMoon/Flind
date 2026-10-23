# Flind — implementation roadmap and release gates

## Mission

Build a dependable independent alternative to PostHog, using the complete imported source as the implementation baseline, not starting over. Support local/self-hosted deployment and eventually an optional hosted offering. This is an execution program, not a claim of completed features.

## Non-negotiable controls

1. Preserve all data and interface semantics while changing brand; migrations require bidirectional compatibility tests where realistic.
2. Use copy-first and reuse upstream behavior before adding or replacing subsystems.
3. Keep the private GitHub repository the source of truth. Temporary local checkouts must be cleaned after durable changes are pushed.
4. Never enable inherited GitHub Actions, paid cloud services, telemetry, external APIs, or production deployments by default.
5. Keep source/copyright/third-party notice integrity. Track founder-permission coverage for restricted source prior to public distribution.
6. Do not label the product beta, production-ready, secure, compliant, faster, or feature-complete without measured evidence.
7. Agent prompts and engineering records are in English; the public-facing product brand is Flind.

## Evidence-based execution phases

| Phase | Scope | Acceptance gate |
| --- | --- | --- |
| F0 — Snapshot | Import all tracked monorepo files into an independent private repo | Matching Git tree and committed source inventory |
| F1 — Identity | Flind README, browser title/manifest, favicon/logo replacements, in-app copy, email template and public asset scan | No visible upstream branding in sampled end-user flows |
| F2 — Runtime | Remove implicit upstream services/secrets, define runnable local Docker profiles and deterministic bootstrap | Fresh local deployment with zero external dependency on upstream SaaS |
| F3 — Data path | Capture → ingest → queue → ClickHouse → query → UI; verify identity and privacy boundaries | Events round-trip with golden fixtures, no loss/duplication outside declared semantics |
| F4 — Product features | Analytics, replay, flags, experiments, errors, surveys, CDP, AI observability, MCP analytics | Feature-specific API, UI, integration and migration suites green |
| F5 — SDK independence | First-party JS, Node and Python paths with explicit compatibility adapters; expand later | SDK contracts verified and old clients can migrate safely |
| F6 — Operability | Auth, billing isolation, rate limits, observability, backup/restore, security hardening, upgrades | Recovery drills, threat model and independent release review |
| F7 — Differentiation | Simpler self-host, stronger agent workflows, privacy UX, fast query experience | Documented comparative benchmarks using repeatable workloads |
| F8 — Release qualification | Docs, accessibility, API reference, packaging, branding and licensing review | End-to-end clean install, upgrade, migration, load tests; explicit release decision |

## Prioritized capability matrix

**Copied code, not validated functionality:** product analytics (events, cohorts, funnels, retention), web analytics, dashboards, HogQL/data query surfaces, session replay and heatmaps, feature flags, experiments, surveys, error tracking, logs, APM and tracing, alerting, data warehouse, CDP integrations and transformations, customer/revenue analytics, LLM/AI observability, MCP analytics, support and agent features.

For each capability, maintain its own status: *present-in-source → builds → local-smoke → integration-tested → release-qualified*. Default is **present-in-source**. Never silently upgrade status based solely on source presence.

## Infrastructure and major risks

Imported code spans Python/Django, React/TypeScript, Node, Rust, Kafka, ClickHouse, PostgreSQL, Redis, Docker, background workers and multiple services. A complete source copy is not yet a supported operational stack. Treat migrations, proprietary `ee/` code, billing, hardcoded external endpoints, inherited GitHub Actions and externally published SDKs as separate release-blocking inventories.

## Flind-specific product opportunities

- **One-command local setup:** verified small-footprint mode and scalable compose mode.
- **Privacy controls:** transparent data destination and retention defaults, straightforward self-host.
- **Agent-ready insights:** safe, permissioned natural-language analysis and MCP interfaces.
- **Unified debugging:** correlate events, replays, errors, traces, experiments and AI calls.
- **Developer experience:** readable onboarding, typed SDKs, golden examples, honest cost metrics.

The differentiation list is a design target. It does not assert that these capabilities are delivered.

## Immediate engineering next actions

1. Finish F1 visible-brand inventory; change reachable app chrome, emails, generated HTML, icons and images with tests.
2. Trace first-run environment variables and external SaaS calls; block production-bound telemetry by default.
3. Build a small, reproducible F2 compose profile; measure memory/disk use.
4. Add event ingest-to-query smoke test and preserve all schema identifiers until migrations are proven.
5. Inventory independent SDK repos and packaging; choose safest compatibility path.
6. Run feature-by-feature REA against PostHog, Amplitude, Mixpanel, Heap, LaunchDarkly, FullStory, Sentry and Langfuse to prioritize measurable improvements.
7. Audit each inherited workflow before enabling CI; start with a minimal audited static and unit-test pipeline.

## Definition of done

Flind is **not done** until a clean environment installs without PostHog-operated services, product workflows pass automated tests, visible branding is independent, public SDKs work, migrations/backup restore succeed, performance is measured, repository notices/permissions are reconciled, and release approval is explicitly recorded.
