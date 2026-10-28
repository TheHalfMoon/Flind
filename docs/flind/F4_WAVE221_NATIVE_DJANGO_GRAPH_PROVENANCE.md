# Wave 221 - native Django migration graph, read-only qualification

## Source and isolated runtime

On 2026-10-28, the source-bound Django probe was run against private Flind
`origin/main` commit `c8eb5c8b70dc257bc99b3badd254de75d572c4b3`
(Wave 220 merged). The Mac marked sparse checkout and Flind-owned Python
3.14.7 venv were used; the original first-party migration staging audit had
verified 3,706 canonical migration blobs and preserved one historic
noncanonical filename. No global package changes or external services.

The probe needed the tracked `packages/personhog-proto` Python workspace on
its **controlled child PYTHONPATH**, plus two small tracked first-party
resources: `products/growth/backend/enrichment/scoring_formula.hog` and
`products/alerts/backend/logic/destination_stock_inputs.json`. They were
materialized only in the marked Flind sparse scratch checkout. Pinned
third-party imports were added incrementally to the owned venv, not globally.
The child still denies network sockets and points service URLs at nonexistent
loopback addresses.

## Genuine first-party probe result

`tools/flind/qualify_sparse_django_registry_wave147.py --root . --ref
origin/main --migration-graph --timeout 85 --max-imports 2600 --json`
returned exit **0** with:

- `source_commit`: `c8eb5c8b70dc257bc99b3badd254de75d572c4b3`
- `django_registry_qualified`: **true**, `app_count`: **115**
- `migration_files_staged`: **3706**
- `migration_graph_qualified`: **true**, `migration_graph_nodes`: **839**
- `migration_graph_disk_items`: **3335**
- `migrations_qualified`: **false**, `app_http_qualified`: **false**
- `real_ingest_qualified`: **false**, `tenant_isolation_qualified`: **false**
- `release_qualified`: **false**

The 3,335 disk items and 839 graph nodes are different Django loader
measurements; neither represents applied database migrations. The
first-party child import path fix is covered by focused regression tests.

## Remaining acceptance

This is **read-only source/registry/graph qualification only**. No original
PostgreSQL or ClickHouse migration was applied, and the original
Kafka/Rust/Node service Jest still has the prior Wave216 **4/4 failures**
from missing schemas. The Windows C disk/WSL I/O gate remains unresolved.
Next use **only ownership-verified disposable Flind** PostgreSQL/ClickHouse
services, apply genuine first-party migrations, rerun original E2E and
then cross-tenant/auth/SDK/browser qualification. Do not touch Zyara,
release, deploy, publish, enable Actions or use paid services.
