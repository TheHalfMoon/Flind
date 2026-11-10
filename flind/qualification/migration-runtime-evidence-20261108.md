# Flind migration runtime qualification — 2026-11-08

Status: **PASSED** on real services. Private qualification only; PUBLICATION HOLD remains.

## Run

| Field | Value |
| --- | --- |
| Workflow | `.github/workflows/flind-runtime-migrations.yml` |
| Run | GitHub Actions run 42428805120 (attempt 1) |
| Source commit | `34c14ab7720178250fe9162b3a8c3cc4755a7576` (main `e8171fc` + this workflow only) |
| Runner | GitHub-hosted `ubuntu-24.04`, private repository |
| Services | Postgres 15.12, ClickHouse 26.9.13.15, Redpanda v25.1.9 (Kafka API), Zookeeper 3.7.0, Redis 7.2 — throwaway containers from `docker-compose.dev.yml` |
| Command | real `bin/migrate --scope=clickhouse --scope=postgres --scope=persons` |

## Results

| Check | Result |
| --- | --- |
| Pass 1, fresh databases | exit 0, `[migrate] outcome: phase=none status=0`, 2031 s |
| Pass 2, over the migrated state (idempotency / upgrade-in-place) | exit 0, Django reports `No migrations to apply`, 212 s |
| ClickHouse ledger `posthog.infi_clickhouse_orm_migrations` | 346 rows, `0001_initial` … `0359_logs_ingest_to_apm` (matches the 346 migration files in source) |
| `migrate_clickhouse --plan` after both passes | `Clickhouse migrations up to date!` |
| ClickHouse tables in `posthog` | 369 |
| Django `showmigrations --plan` | 839 applied, 0 pending |
| `makemigrations --check --dry-run` | `No changes detected` (models match migrations) |

## Earlier runs on this branch (kept for honesty)

- 42421540030 — failed: workflow installed `--no-dev`, but `DEBUG=1` settings load `django_linear_migrations`. Workflow bug, not product.
- 42425580117 — both migration passes succeeded (1524 s / 145 s); verification query used a wrong column (`name` vs `module_name`). Workflow bug, fixed.

## Findings to follow up

1. **Branding leak:** startup warning prints "PostHog is running in DEVELOPMENT MODE!".
2. **Fresh-install noise:** GeoIP2 database is absent, so every management command logs a `GeoIP2Exception` traceback. Non-fatal, but should be a clean single warning or a bundled/optional database.
3. Account Actions artifact storage quota is full; evidence is therefore kept in the job summary and in this file.

## Not covered by this run

Rust-side migrators (cyclotron, behavioral cohorts, flags read store), async migrations, multi-node ClickHouse, macOS/Windows hosts, ingestion, APIs, and browser E2E.
