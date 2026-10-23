# Flind

**Product intelligence, experimentation, and observability — in one platform.**

Flind is an independent product platform under active development. Its goal is to unify analytics, session replay, feature flags, experiments, error tracking, data pipelines, AI observability, and agent-ready product context.

> **Status: private pre-alpha. Not production-ready.** The initial codebase has been imported in full from a pinned source snapshot, but functional parity, independent operation, rebranding, and release safety have **not** been verified. No deployment or performance claims are made yet.

## Product surface under validation

| Area | Intended Flind capability |
| --- | --- |
| Understand | Product and web analytics; funnels, cohorts, retention, dashboards, SQL |
| Observe | Session replay, heatmaps, errors, logs, tracing, alerts |
| Experiment | Feature flags, controlled rollouts, A/B experiments |
| Engage | Surveys, messaging, workflows, support context |
| Connect | Ingestion APIs, CDP, warehouse integrations, exports |
| Build with AI | LLM observability, MCP analytics, agent-oriented product intelligence |

The source snapshot includes code paths for these areas; each must pass its own operational acceptance tests before Flind can claim to support it.

## Engineering principles

- **Copy first, then improve:** retain proven behavior and interfaces while establishing an independent Flind platform.
- **Preserve data:** no unsafe schema, event, or SDK renames without migrations and compatibility tests.
- **Self-hostable by design:** independently deployable infrastructure with explicit data ownership and privacy controls.
- **Cost controlled:** no automatic cloud billing or CI runs; opt in to infrastructure only after a budget review.
- **Evidence before release:** verification records and measurable gates are mandatory.

## Working on Flind

Start with [the foundation roadmap](docs/flind/FOUNDATION.md) and [the rebranding inventory](docs/flind/REBRAND_INVENTORY.md). The [source baseline](docs/flind/SOURCE_BASELINE.md) identifies the complete initial import.

Validate the first brand entrypoints with:

```bash
python3 tools/flind/check_brand_entrypoints.py
git diff --check
```

A supported standalone installation path is not yet available. Existing deployment scripts from the imported source must be audited before use.

## Licensing and provenance

Flind retains relevant source and third-party notices, including [LICENSE](LICENSE) and [ee/LICENSE](ee/LICENSE). A separate permission grant is founder-asserted for the full-source use; the recorded scope must be confirmed before redistribution or commercial release of restricted components. Development changes remain separate from the pinned import.
