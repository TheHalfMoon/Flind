# Wave 75 — Sustained, bounded Django migration qualification

## Why

The previous 5 × 120-second isolated PostgreSQL test recorded **3,046**
committed migration rows, but timed out before Django completed its graph.
Every restart invokes heavyweight Django app setup and migration loading.

Wave 75 provides a complementary, opt-in test that can use **longer
individual migration subprocesses** before a bounded retry. It does not
fake or skip any migrations, change their ordering, modify product apps,
use the system PostgreSQL service or retain a disposable database.

## Reproduction

With the exact frozen Python 3.14.7 environment, required packages
and authorized full source checkout:

```sh
# 1 × 360-second subprocess (default):
python -m tools.flind.qualify_sustained_migrations_wave75 --json

# Explicit, resource-admitted longer retry window, only if needed:
python -m tools.flind.qualify_sustained_migrations_wave75 \
  --rounds 2 --seconds 360 --json
```

The outer guard requires **10 GiB free /tmp** before creating a cluster.
The existing runner keeps its minimum **2.5 GiB live disk guard** and
process-group SIGTERM/SIGKILL shutdown, while PostgreSQL's
`isolated_postgres` wrapper creates and destroys the localhost-only,
random-port SCRAM-authenticated test database.

A bounded retry occurs **only** if the previous subprocess reached the
migration phase, timed out normally, increased the independently verified
committed-row count, and emitted no recognized Django exception.
Database count regression, no progress, invalid receipts and actual
Django error classes stop immediately. All outer input validation uses
strict exact integers, 1–3 rounds and 60–360 seconds per subprocess.

One database persists across rounds of the same invocation, but is
deleted at the end. Only sanitized migration IDs, counts and status
bits appear in reports; no credentials, SQL, URLs or raw logs.

## Evidence and boundaries — October 25, 2026

- 37/37 focused Wave 75 and existing migration/detection tests PASS.
- **Executed the new Wave 75 orchestrator itself** on a freshly created
  disposable PostgreSQL 17 cluster, with 1 × 120-second Django run:
  **2,491 committed rows**, real `django_stage_seen=true`,
  no Django error, `full_schema_migrations_completed=false`,
  `release_qualified=false`. The private DB was destroyed.
  This independently verifies the fix against a migration log much longer
  than the 180-line diagnostic tail.
- The exact frozen runtime and real PostgreSQL 17.9 are available locally.
- Actual 360-second single-process baseline against a new disposable
  PostgreSQL 17 database committed **2,806 migration rows** before its
  bounded timeout. Last committed `data_modeling.0053_job_team_created_index`.
  This **did not** finish the graph, so release remains NO-GO.
- Earlier five 120-second rounds accumulated 3,046 rows in 600s.
  These figures are *different fresh databases* and do not prove a
  comparative speedup by themselves: migration costs vary by app and order.
- The 360-second baseline exposed a real telemetry error: earlier code
  reported `django_migration_stage_seen=false` despite 2,806 committed
  migrations because the stage marker had scrolled beyond the last 180
  lines. Wave 75 scans **all** log lines for that exact marker while
  still returning only the sanitized diagnostic tail. New long-log
  regressions reproduce and prevent that false startup-blocker report.
- Do not infer schema completion from increased migration rows alone:
  `full_schema_migrations_completed` may be TRUE only after Django
  exits successfully and the private database receipt independently
  shows committed migration rows.
- `release_qualified` is hard-coded **FALSE**, even if full schema
  succeeds; Flind still requires real SDK/Kafka/ClickHouse ingestion,
  query/dashboard, auth/tenant isolation and frontend/browser E2E.

No paid provider, external deployments, shared PostgreSQL changes,
publication, or removal of required legal source attribution. Keep
the repo private and inherited GitHub Actions disabled. Issue #82
remains OPEN. PR #99 can remain draft until separately fully qualified.
