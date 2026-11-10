# Upstream delta: Flind import to pinned cutoff

- Flind import point: `cd26680c84533f65f43e1c7efc701bf792a5363a` (PostHog/posthog, 2026-10-23)
- **Pinned cutoff: `4efa693e9aecb76ad4321120df2201414b41737b`** (PostHog/posthog `master`, 2026-11-10T04:40:27Z)
- Commits between them: **4189**
- Files changed: **36303** (added 16658, deleted 8861, modified 10784)
- Also changed by Flind since import (conflict surface): **2289** files

Method: depth-1, blob-less fetches of both commits and `git diff --no-renames --name-status`; Flind's own changes are
`main` against the same import commit. `upstream-delta.jsonl` has one row per file with `disposition: unreviewed`;
each integration PR updates the rows it covers (`incorporated`, `needed`, `adapt`, `conflicting`, `superseded`,
`unnecessary`, `blocked`). The cutoff is fixed for release qualification; later upstream commits are out of scope.

## By kind

| Kind | Files |
| --- | ---: |
| source | 26357 |
| test | 9260 |
| migration | 369 |
| ci | 217 |
| dependency | 100 |

## By area (top 30)

| Area | Files | Also changed by Flind |
| --- | ---: | ---: |
| `products/warehouse_sources` | 17401 | 3 |
| `frontend/src` | 2850 | 795 |
| `products/mobile` | 1600 | 0 |
| `products/signals` | 940 | 112 |
| `products/ai_observability` | 689 | 107 |
| `products/desktop` | 609 | 306 |
| `products/workflows` | 569 | 85 |
| `services/mcp` | 559 | 14 |
| `nodejs/src` | 517 | 15 |
| `products/product_analytics` | 470 | 81 |
| `products/replay_vision` | 442 | 49 |
| `products/experiments` | 342 | 18 |
| `products/dashboards` | 262 | 3 |
| `products/tasks` | 250 | 11 |
| `products/posthog_ai` | 240 | 32 |
| `products/web_analytics` | 215 | 10 |
| `products/error_tracking` | 205 | 23 |
| `posthog/api` | 200 | 33 |
| `packages/quill` | 197 | 25 |
| `posthog/temporal` | 187 | 0 |
| `posthog/hogql` | 184 | 2 |
| `products/slack_app` | 178 | 1 |
| `posthog/models` | 177 | 6 |
| `products/mcp_analytics` | 176 | 39 |
| `hog/test` | 172 | 0 |
| `hog/src` | 162 | 0 |
| `products/data_warehouse` | 162 | 35 |
| `products/marketing_analytics` | 156 | 30 |
| `products/customer_analytics` | 154 | 24 |
| `posthog/clickhouse` | 146 | 2 |

## Integration order

1. **Security fixes**: identified from commit messages in the range; integrated first, each with a regression test.
2. **Migrations** (`kind: migration`): Django and ClickHouse migrations in order, qualified by the real-service
   migration workflow (`makemigrations --check`, ClickHouse plan, idempotent re-run).
3. **Areas without Flind changes**: taken as upstream has them, area by area, with that area's tests.
4. **Conflict surface**: one area per PR, preserving Flind's rebrand, legal-copy and runtime-independence changes;
   the brand, legal-claim and Flind guards must stay green.
5. **Dependencies and CI**: lockfile and workflow changes last, re-verified with the frozen-lockfile installs.

`products/warehouse_sources` dominates the file count (generated source connectors); it is integrated as its own unit.
