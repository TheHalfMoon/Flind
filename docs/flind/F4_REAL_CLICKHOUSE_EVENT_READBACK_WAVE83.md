# Wave 83 — Actual isolated ClickHouse event-column readback

## Scope and execution

On the authorized Mac, native ClickHouse
**26.10.2.103** was available. Wave 83 extends Flind's existing
temporary, loopback-only ClickHouse fixture with an optional
`on_ready(port)` callback: it runs after the established
SELECT/CREATE/INSERT/READ/DROP probe and before the isolated server
is terminated and its temporary directory destroyed. Errors from a
probe abort qualification; cleanup executes in `finally`.

The new `qualify_event_store_wave83.py` performs an **actual** synthetic
event-column readback in the isolated ClickHouse HTTP server, not
an in-memory fake or purely mocked database. It first checks the
six canonical columns against the actual
`posthog/models/event/sql.py:EVENTS_TABLE_BASE_SQL` source:

`uuid UUID`, `event VARCHAR`, `properties VARCHAR`,
`timestamp DateTime64(6, 'UTC')`, `team_id Int64`,
`distinct_id VARCHAR`.

For this **component** qualification only, the six compatible fields
are projected into an isolated, explicitly named ClickHouse
`ENGINE=Memory` table. This is **not** the full production
`sharded_events` / JSON / Kafka / distributed schema, and no actual
person/event data is used.

The probe inserts six fixed synthetic events (`$pageview`,
`$pageleave`, `purchase`) from two teams (101 and 202), deliberately
including the same `distinct_id` on both teams. It then issues
team-scoped aggregate queries and cross-team path-negative queries
and checks all results exactly. Finally it drops the test table
whether its readback succeeds or fails.

## Actual observed local result (2026-10-25)

```
isolated_clickhouse_passed                   true
real_flind_shaped_event_readback_qualified   true
synthetic_events_inserted                    6
team 101  events=4 pageviews=2 unique_ids=2 purchases=1
team 202  events=2 pageviews=2 unique_ids=2 purchases=0
cross_team_path_readback_absent              true
colliding_distinct_ids_scoped                true
temporary_database                          true
sdk_ingestion_qualified                      false
kafka_ingestion_qualified                    false
dashboard_query_qualified                    false
release_qualified                            false
```

Both team-filtered queries excluded the other team's path despite
shared synthetic distinct ID. **This tests correctly scoped queries;
it does not establish database-enforced row-level permissions or
application-level multi-tenant authorization.** All ClickHouse process
and test data were temporary and loopback-only.

## Regression evidence

- **19/19** focused Python unit tests PASS: canonical source-field
  mismatch refusal, exact bounded SQL statements and synthetic
  input guards, query parameter rejection, strict 64-bit team ID
  limits, cross-team leak/mismatch failure, unconditional DROP even
  on errors, refusal of forged success, callback lifecycle and
  guaranteed termination, plus all existing isolated ClickHouse
  Wave 50 unit tests.
- **Actual isolated ClickHouse roundtrip PASSED** with event payloads
  and aggregate readback in `~5 seconds`.
- Existing baseline isolated ClickHouse component test also PASS,
  with three-row SQL readback and local memory bounds intact.
- Python source passes syntax and whitespace verification.

## What remains NO-GO

The explicit backend release-blocking gates are **not** cleared.
This wave does NOT run a captured browser/SDK payload, a Kafka topic,
a ClickHouse materialized view, the production full event schema,
Django API/authorization, a real Flind dashboard readback, full
Django migration graph, full frontend bundle, or full E2E.
`release_qualified` remains false by design.

No public deployment, shared database, paid service, system install,
external network egress or user datasets were involved. Preserve
private GitHub repository, disabled inherited GitHub Actions and
required LICENSE/NOTICE source attribution. Keep release Issue #82
open and use this narrow reproducible component test as the next
building block for end-to-end ingestion qualification.

To rerun on a Mac with local ClickHouse and enough free disk:

```sh
python3 -m unittest tools.flind.test_event_store_wave83 tools.flind.test_ephemeral_clickhouse_wave50 -q
python3 tools/flind/qualify_event_store_wave83.py --json
```
