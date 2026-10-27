# Flind Wave 172 — Actual current-main Django migration graph loading

## Qualification result — 2026-10-27

**PASS: Django migration graph source loading only**, on the first-party private Flind `main` commit `1905e9afb0f25f2685f042485b59f4c433403ffe`, under the same isolated pinned Mac Python3.14.7 / Django5.2.18 runtime used to qualify Wave171. Nothing was executed against a PostgreSQL database.

Observed proposed-source **`--migration-graph`** receipt:
```json
{
  "phase": "sparse-git-django-app-registry",
  "source_commit": "1905e9afb0f25f2685f042485b59f4c433403ffe",
  "django_registry_qualified": true,
  "app_count": 116,
  "migration_files_staged": 3706,
  "migration_graph_disk_items": 3335,
  "migration_graph_nodes": 839,
  "migration_graph_qualified": true,
  "migrations_qualified": false,
  "app_http_qualified": false,
  "real_ingest_qualified": false,
  "tenant_isolation_qualified": false,
  "release_qualified": false
}
```

Numbers are different because the Git tree inventories **tracked Python files** (including `__init__.py`), Django's `MigrationLoader(None)` discovers **migration definitions** from registered apps, and Django's graph **nodes** account for migration replacements/squashing. These metrics must not be substituted for one another.

## Verified source/migration hydration

A fresh, disposable sparse clone of the actual private Flind `main` was used. Its initial Git object directory was only about 2.8 MiB and `pyproject.toml` was materialized explicitly. Read-only local Git alternate objects supplied most real tracked current-main Python contents; implicit network fetching was denied with `GIT_NO_LAZY_FETCH=1`. Two known non-Python resources, `scoring_formula.hog` and `destination_stock_inputs.json`, were copied into the **isolated scratch clone only**, after matching each object's SHA-1 against the exact new main Git tree.

Read-only Git migration inventory for the pinned Flind commit:
- **3,707 migration-looking tracked Python paths**;
- **3,706 canonical, safe migration source paths** to stage;
- one noncanonical historical path `posthog/clickhouse/migrations/0067_event_kafka_debug_table copy.py` (contains a space) **was reported and not written or renamed**. It is an independent source hygiene question; preserve until qualification, do not blindly delete migration history.
- **3,706 / 3,706 local canonical Git blobs available**, **0 physical** at start, total **15,815,118 bytes**.
- Grouped tracked canonical paths: `posthog=1680`, `products=1956`, `ee=70`.

The new `tools/flind/stage_migration_sources_wave172.py` verifies local-only tree metadata, type, blob sizes, total budget, and full Git object digests. A **marked disposable Git checkout** is mandatory for opt-in `--materialize`; an unmarked checkout cannot be modified. It rejects bad ref, unsafe paths, symlinks, modified/conflicting tracked files, absent blobs and resource budget overflow. Dry run writes nothing. The actual staging run restored **3,706 exact canonical migration source files** (15.8 MiB) into the isolated scratch clone, **without modifying any other user's checkout or invoking SQL**.

The separate opt-in `--migration-graph` flag on the existing Django sparse registry qualifier refuses to report graph success until it sees the explicit marker and all canonical tracked migration Python files in the disposable checkout. It then invokes **`django.db.migrations.loader.MigrationLoader(None)` with a null database connection** inside the existing socket-denied, timeout-bounded Django process. Errors are reported as sanitized type names without printing secrets. Without this flag the normal registry probe remains just a registry probe.

## Actual tests

The exact Wave172 proposed Python code was loaded into a disposable Mac test runner:
- **25/25 Python unit tests PASS** across the existing Django importer tests and new migration-source staging tests, under `-W error::ResourceWarning`.
- Current Flind source Git migration preflight **PASS**, 3,706 validated blobs available.
- Marked scratch hydration **PASS** and wrote 3,706 tracked canonical migration Python files.
- Actual current-main `django.setup()`: **PASS**, 116 registered apps.
- Actual opt-in `MigrationLoader(None)`: **PASS**, 3,335 disk migration records, 839 graph nodes, 3,706 staged canonical Python migration files.
- No production or even disposable PostgreSQL migration execution/rollback was undertaken. No ingestion, user tenancy query, web UI or public OAuth sign-in was tested.

## Release gates

The status **`migration_graph_qualified=true` must never set `migrations_qualified=true`**. Next steps: explicitly provision a disposable, isolated PostgreSQL cluster; run migration apply and rollback with dedicated credentials and no shared user DB access; qualify Redis/Kafka/ClickHouse + SDK→tenant-authenticated API→Dashboard; cross-tenant isolation and Playwright/desktop tests; then final source/distribution identity audit.

Keep #82 and #5 open, release **NO-GO**. Repo PRIVATE, inherited GitHub Actions disabled, no publication/deployment/paid services. Preserve mandatory third-party licenses.
