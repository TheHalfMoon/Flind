# Flind Wave 177 — Source-backed isolated ClickHouse synthetic team predicate queries

## Scope

This wave runs **real ClickHouse 26.10.2 SQL** without a server using `clickhouse local`, with only **synthetic events**. Its event projection is checked against a tracked, Git-blob-digest-verified **first-party Flind `events_recent` HCL definition** at `posthog/clickhouse/hcl/roles/coshared/events_recent/tables.hcl`. The HCL definition includes `uuid UUID`, `event String`, `properties String`, `timestamp DateTime64(6, 'UTC')`, `team_id Int64`, `distinct_id String`. It is **not** a production ClickHouse cluster with materialized views, sharding, Kafka engines, or real ingestion.

Actual authorized Mac testing on 2026-10-27:
- Existing local ClickHouse executable version **26.10.2.103**; no daemon, deployment, database provisioning or network use.
- Git-backed source checkout at exact verified commit `1905e9afb0f25f2685f042485b59f4c433403ffe`, a predecessor of the current main. The 6 expected column names and types were verified against a local-only tracked Git blob, with exact Git SHA-1 digest. The tool **does not claim current main** beyond this verified source commit.
- **Four synthetic event rows** belonging to distinct numeric teams **101** and **202** loaded into a short-lived ClickHouse local `events` table. No personal/user/health/customer data.
- Five actual bounded ClickHouse local queries: team 101 events, team 202 events, team 101 aggregate count, team 202 aggregate count, and nonexistent team 303 aggregate.
- **PASS**: returned exactly two events/count=2 for each actual team; no event row crossed team boundaries, and team 303 returned zero rows.
- Entire actual proposed executable `tools/flind/qualify_local_clickhouse_tenant_sql_wave177.py` returned exit code **0** with `schema_from_tracked_flind=true`, `clickhouse_local_engine_qualified=true`, `synthetic_team_predicates_qualified=true`; runtime approximately **5.5 seconds**, scratch engine files approximately **144 KiB**.
- **12/12 Python unit tests PASS** with `-W error::ResourceWarning` using disposable real Git source fixtures for tracked schema identity/type drift, injection attempts, exact numeric `team_id` validation, no unscoped SQL query generation, missing/symlinked marker refusals and wrong ClickHouse executable.

## Safety model

Only an explicit, marker-protected directory under `/private/tmp` and a separate, verified Git repository under that scratch root are admitted. A source ref must resolve locally; `GIT_NO_LAZY_FETCH=1` and `GIT_TERMINAL_PROMPT=0` stop invisible network fetch. The tool loads only the approved six column shape from the verified `events_recent` HCL file. Synthetic fixtures are temporary; no production ClickHouse paths are queried. Actual SQL is not provided by users: `scoped_sql()` accepts only a positive, bounded **actual integer** team ID and one of `events` or `counts`, and always places a `WHERE team_id = <verified integer>` predicate before running an offline, bounded ClickHouse process with a 128MiB query memory limit and 30-second subprocess timeout. No API authentication is involved.

## Explicitly NOT qualified

- This test **does not prove real tenant authorization**, user credential binding, row-level security at the Flind Django/API layer, or the absence of bugs in unrelated analytics SQL.
- **No real Kafka/Redpanda broker, first-party SDK ingress, schema consumer, ingestion pipeline, materialized events table, query API, dashboard or browser/desktop E2E was run.**
- Full supported PostgreSQL migrations + rollback, OAuth/PKCE/JWKS, worker product tasks, and release artifact naming remain open. Avoid interpreting this synthetic SQL separation test as production isolation.

Next priority: qualify a real, isolated Kafka/ClickHouse ingestion path using Flind's first-party handlers; then tenant-authenticated API/UI and full migrations/rollback. Release issue #82 and identity issue #5 remain **OPEN / NO-GO**. Repo stays PRIVATE with inherited GitHub Actions disabled; no deployment, publication, paid compute/models or legal attribution removal.
