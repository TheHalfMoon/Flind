# Wave 54 — Independent PostgreSQL cluster and Django migration-plan admission

## Boundary

The authorized Mac has a separate PostgreSQL 17 server used by other
work. Wave 48 proved read-only connectivity to that server, but Flind
must NOT create schemas, apply migrations, or run tests there.

Wave 54 creates an entirely isolated temporary PostgreSQL 17 cluster
with its own password, user, random 127.0.0.1-only port, test database,
data path, socket path, and bounded 32 MiB shared buffers.

- initdb uses SCRAM authentication and a randomly generated password in
  a temporary file, not the existing system cluster.
- This private cluster has no external interface; autovacuum disabled
  for the brief test, fsync disabled for disposable data.
- A REAL psql transaction creates a temporary table, inserts three rows,
  reads back count=3 and sum=14, and rolls back.
- PostgreSQL is stopped and its temporary directory deleted in finally,
  including failure paths. No global PostgreSQL service is restarted.

## Optional Django application layer

Run with the fully locked Python 3.14.7 environment:

    python tools/flind/qualify_ephemeral_postgres.py --json
    python tools/flind/qualify_django_pg_plan_wave54.py --json

The second command requires exact direct dependency lock parity and
starts its own isolated cluster. While that cluster is running, it
executes Django's read-only showmigrations --plan. An ephemeral
SECRET_KEY is provided and REDIS_URL points to a dummy loopback port;
FLIND_READINESS_CHECK disables startup catalog queue side effects.

The test returns only counts/status and a bounded error class; no
database password, credentials or session content is printed.
No Django migrate or schema write is permitted by the probe.

## Executed evidence, October 24, 2026

- Isolated PostgreSQL 17.9 startup: PASS.
- SCRAM password + separate data directory/loopback port: PASS.
- Independent test DB creation and transactional SQL readback: PASS,
  3 rows with total 14.
- Transaction rolled back, temporary cluster stopped, files cleaned.
- Live Django migration-plan read against an empty isolated DB: PASS.
- 839 migration-plan entries; no migrations applied.
- Both temporary PostgreSQL and Django plan probes returned success.
- Focused PostgreSQL isolation and Django plan tests: 11/11 PASS.
- Full Flind Python regression suite: 416/416 PASS.

## Still NO-GO

A migration plan is not an applied migration. The separate Django app,
Redis/Celery, Kafka, ClickHouse data stream, SDK capture/query parity,
auth/tenant isolation and browser/desktop/mobile E2E remain blockers.
Do not run destructive migrations on the existing PostgreSQL service.

The GitHub repo stays private, inherited Actions disabled; no
publication, deployment, paid providers or user-data changes.
