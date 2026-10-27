# Wave 173 — Isolated real PostgreSQL read-only migration plan and reversible Flind migration

## First real PostgreSQL qualification on Flind — 2026-10-27

For the first time in the F4 development series, the actual Django application successfully connected to an intentionally separate native **PostgreSQL 17.9** cluster and applied and rolled back a **real first-party Flind migration**. This is **scoped migration smoke qualification, not full migration execution or release approval**.

Pinned first-party source: private Flind `main` commit `1905e9afb0f25f2685f042485b59f4c433403ffe`, in the marked, sparse, disposable source checkout that Wave171 used for registry qualification and Wave172 used to stage 3,706 verified migration Python files. The two required non-Python startup resources are also Git-verified and materialized only inside this scratch clone.

## Strict database isolation

An **entirely new** cluster was initialized at `/private/tmp/flind-wave173-isolated-postgres` with its own `PG_VERSION` and marker `.flind-isolated-pg-v1` containing `FLIND_ISOLATED_PG_V1`. The isolated PostgreSQL server was started with **`listen_addresses=''`** (no TCP), a dedicated Unix socket directory `/private/tmp/flind-wave173-socket`, and port `65443`. A disposable database named `flind_wave173_synthetic` was created. This deliberately did **not** touch the Mac's independently running system PostgreSQL and PgBouncer processes or their databases.

The Wave173 qualification script requires exact, marker-protected source and data directories under `/private/tmp`; a dedicated Unix socket file; an explicitly synthetic, tightly patterned database name; and an initial checked Git source commit. It refuses unmarked databases, source/database overlap, shared system Postgres locations, TCP targets, and unexpected database configurations. It denies Python TCP sockets and attempts to contact unrelated Redis/Kafka/ClickHouse endpoints. Before reading a migration plan, it verifies the connected database identity, its PostgreSQL server data directory, Unix-socket-only status, and a **read-only session**.

Command executed with the exact proposed Wave173 source in the existing pinned Python3.14.7 / Django5.2.18 environment (no new paid services):

```sh
python tools/flind/qualify_isolated_postgres_wave173.py \
  --root /private/tmp/flind-wave171-current-boot \
  --ref HEAD \
  --pg-data /private/tmp/flind-wave173-isolated-postgres \
  --pg-socket /private/tmp/flind-wave173-socket \
  --pg-port 65443 \
  --dbname flind_wave173_synthetic \
  --apply-rollback --json
```

## Verified results

| Stage | Actual result |
|---|---|
| `django.setup()` | PASS — 116 registered apps |
| Migration source preflight | 3,706 physically staged canonical Git files |
| Django migration graph | PASS — 3,335 disk migrations, 839 graph nodes |
| Real PostgreSQL socket connection with exact data-directory identity | PASS — read-only |
| Read-only, empty-database full migration plan | PASS — 839 planned migrations across 92 leaf targets |
| First-party `ai_training.0001_initial` real migration application | PASS |
| First-party `ai_training.0001_initial` real migration rollback | PASS |
| Applied migration records remaining for that app | **0** |
| Other user tables remaining after rollback | **0** |
| Full migration application and full rollback | **NOT QUALIFIED** |
| Real Redis/Kafka/ClickHouse ingestion, HTTP/API/Dashboard/tenancy | **NOT QUALIFIED** |
| Release | **NO-GO** |

The only writable database operations were performed **after verifying the exact local scratch PostgreSQL data directory and marker**, while intentionally enabling writes in the isolated session. The script permits **only** the inspected, dependency-free `ai_training.0001_initial` migration containing one safe `CreateModel` operation. It always attempts reversal of that one scoped migration, then independently verifies zero leftover migration records or app user tables. The `django_migrations` bookkeeping table may remain empty after rollback. No bulk migrations or customer data were touched.

During Django app startup, a few inherited background initializers attempted fake Redis connections; the socket-deny policy prevented these. This is **not** proof that worker/Redis startup is healthy and remains separately blocked.

## Exact executable verification

- Original Wave171 Django importer tests, Wave172 migration hydration tests and Wave173 isolated PostgreSQL admission/selection tests: **30/30 PASS**, no skips, `-W error::ResourceWarning`.
- Actual Wave173 proposed code on isolated PostgreSQL: **PASS**, real read-only migration plan and selected migration apply+rollback, exit 0.
- Independent PostgreSQL query after rollback confirmed `django_migrations` row count **0**, non-bookkeeping public user tables **0**, and Unix socket `inet_server_addr() IS NULL`.
- The source commit was revalidated as `1905e9afb0f25f2685f042485b59f4c433403ffe`. No false claim that the source was a full non-sparse distribution or that all migrations ran.

## What is still required

To qualify the entire Flind app: run all supported migrations with reversal safety on **fully isolated**, adequately resourced PostgreSQL; qualify explicit supported versions of Redis/Kafka/ClickHouse, SDK ingestion, per-tenant authenticated API/queries and dashboard results, error recovery, browser/desktop E2E and first-party OIDC/PKCE. Final product/SDK/installer/asset/legal-notice identity audit remains separate. In particular, the presence of a noncanonical migration file name identified in Wave172 is unresolved and should not be blindly renamed or deleted.

**Keep release blocker #82 and identity issue #5 OPEN.** Repo PRIVATE, inherited GitHub Actions disabled, no publishing/deployment or paid services. Preserve mandatory third-party license notices.
