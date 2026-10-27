# Flind Wave 178 — Actual offline ClickHouse Memory-engine INSERT + scoped SELECT

## First source-backed SQL write test on 27 October 2026

Wave177 already qualified *read-only* `clickhouse local` queries over a synthetic JSONEachRow source file, checked against the first-party tracked `events_recent` HCL schema. This wave advances to an **actual SQL `CREATE TABLE` and `INSERT INTO`** followed by multiple team-scoped `SELECT` statements in the same bounded ClickHouse local process.

Actual resource-limited Mac execution:
- ClickHouse local executable **26.10.2.103** (no server daemon, TCP/HTTP listener, Kafka or cloud resources).
- First-party events schema, read by offline Git commands and verified by exact blob SHA-1 at private Flind commit `1905e9afb0f25f2685f042485b59f4c433403ffe` (historical baseline, **not** proof of a refreshed current-main source).
- `CREATE TABLE events` with source-backed `uuid UUID`, `event String`, `properties String`, `timestamp DateTime64(6, 'UTC')`, `team_id Int64`, `distinct_id String` and **`ENGINE = Memory`**.
- `INSERT INTO events (...) VALUES (...)` with **four hardcoded synthetic** events, two belonging to numeric team 101 and two belonging to team 202.
- 5 scoped SELECTs: counts for 101 and 202, event rows for each of 101 and 202, and nonexistent team 303. Exactly two events per actual team and zero events from other teams or nonexistent team 303. None of these SELECTs can be invoked via untrusted SQL strings: all allowed statements are constructed from fixed templates, validated numeric team IDs and two known query variants in Wave177.
- **7 SQL statements** (CREATE, INSERT, 5 scoped SELECTs), real ClickHouse Memory engine.
- Exact proposed standalone executable `tools/flind/qualify_local_clickhouse_insert_wave178.py` tested **twice with exit code 0**, reporting `first_party_schema_verified=true`, `real_clickhouse_insert_qualified=true`, `synthetic_team_query_qualified=true`, and `synthetic_inserted_rows=4`. Observed successful elapsed times approximately **13.8s** and **9.3s**.
- **24/24 original Python unit tests PASS** across Wave177 and Wave178 suites, `-W error::ResourceWarning`, including invalid/team-injection, schema drift, malicious/missing marker, source/scratch scope, invalid fields and row counts, SQL value quote escaping, and mock-closed executable tests.

## Startup hang and fix

Earlier experimental MergeTree `clickhouse local --queries-file` invocation stalled in the resource-constrained environment and was explicitly stopped. Several Wave178 **standalone** `clickhouse local --multiquery --query` attempts then hit their 18-second timeout even though equivalent runs under Python `python - <<'PY'` completed instantly. The cause was an open inherited **stdin** stream when the script ran normally: ClickHouse local's multiquery mode could continue reading it, whereas heredoc runs naturally reached EOF.

The final merged candidate explicitly passes **`stdin=subprocess.DEVNULL`** and redirects stdout/stderr to bounded files within the marked scratch directory (no inherited subprocess pipes). The bounded 18-second child execution limit and 128MiB ClickHouse query memory setting remain. Source/path and output conflicts fail closed. Subsequent **two full standalone tests PASS**. Failed preliminary experiments are not counted as passes and no MergeTree persistence or service integration is claimed.

## Safety and limitations

- Only a marker-protected temporary scratch folder under `/private/tmp` is admitted. The source repository is separately located, read-only, and its exact commit and schema Git blob checked with lazy fetch disabled.
- Only synthetic, non-sensitive event values. No app secrets, real users, databases, network brokers or external services touched.
- This is **not a persistent ClickHouse MergeTree table or cluster**. Memory engine data is discarded when the local process exits.
- **No SDK HTTP capture, Kafka producer/consumer, real Flind ingestion, Django authenticated API query, tenant identity enforcement or dashboard/browser E2E** is qualified. Passing two fixed team ID query cases does not prove production row-level authorization.
- Full migrations/rollback, production worker flows, owner-controlled OAuth/PKCE/JWKS, final Flind branding/artifact scan and legal notices remain independent release gates.

Issue **#82** stays OPEN for service-backed SDK→Kafka→ClickHouse→tenant-authenticated API→dashboard, durable ingestion/consistency, full PostgreSQL migrations/rollback and browser/desktop E2E. Issue **#5** stays OPEN for final product/SDK/packages/source artifacts/UX branding. **Release NO-GO**; repo PRIVATE, inherited Actions disabled, no deployment, publication, paid compute or deletion of mandatory donor legal attribution.
