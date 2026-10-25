# Wave 55 — Bounded Django schema migrations in a disposable cluster

## Purpose

Wave 54 proved Django could read a migration plan of 839 entries against
a freshly initialized PostgreSQL 17 database. This does NOT prove that
the inherited schema migrations actually apply, especially given
extensions, functions and external consumers required by Flind.

This wave attempts the real Django migrate management command on an
**independent, disposable** PostgreSQL cluster. No production schema,
system Postgres database, user data or other service is modified.

## Safety

- The disposable database is created by the Wave 54 SCRAM-authenticated
  test-cluster helper. The server is bound to a random loopback port,
  has its own data/socket directory and is stopped in finally.
- A one-use Django SECRET_KEY is passed only through the subprocess
  environment. The database URL points to the disposable cluster.
- Redis, Kafka and ClickHouse endpoints point at non-service localhost
  ports. No cloud API key or third-party account is inherited.
- FLIND_READINESS_CHECK=1 skips catalog synchronization queues during
  startup, not the migration commands themselves.
- The migration process is killed automatically if the test passes its
  configured time limit or disk free space drops below 2.5 GiB.
- A PostgreSQL read-only count of django_migrations in the disposable
  database is the observable receipt. The command's exit status alone
  cannot qualify the schema.
- All generated schema/data is destroyed with the temporary directory
  after returning the receipt.

Reproduce using the fully locked Python 3.14.7 environment:

    python tools/flind/qualify_isolated_migrations_wave55.py --json --max-seconds 145

## What a successful result can establish

That the Django migration command applied migration records to one
isolated PostgreSQL instance. It still cannot prove SDK ingestion, data
processing, ClickHouse event readback, auth/OAuth and tenant isolation,
or a production-safe deployment configuration.

## Executed evidence, 25 October 2026

- A full-schema migration attempt on the isolated cluster ended at
  the bounded time limit. 2,610 django_migrations rows were present in
  the temporary database at shutdown. NOT a complete migration.
- A repeatable diagnostic run with --max-seconds 145 ended at the
  explicitly configured time cap, with 2,541 committed rows and last
  verified committed migration
  posthog.1354_datadeletionrequest_hogql_query_and_more.
- The migration count is a database-row receipt, **not** the number of
  migrations left nor a proof that the schema is consistent at release.
  The earlier showmigrations --plan output of 839 is a distinct
  read-only planning measurement; do not equate the two counts.
- Both attempts exited nonzero with release_qualified=false, killed
  their migration child process, stopped private PostgreSQL, and
  removed its data directory. No isolated server remains running.
- All endpoints besides the owned private PostgreSQL were closed
  loopback placeholders, and no installed cloud credentials were used.
- The bounded diagnostic now supports --max-seconds 20..360 and reports
  the last committed migration name while keeping the DB password
  out of JSON/log output.
- Focused migration/lifecycle tests: **8/8 PASS**.
- Full Flind Python regression suite: **424/424 PASS**.

## Remaining work

Qualify all schema migrations and required PostgreSQL extensions,
dependency service start/stop behavior, real event capture/query
integration, CSRF and frame/TLS policies, frontend distribution and
device E2E as tracked by issue #82. This project is NO-GO for release.

No public deployment, paid services, persistent Flind databases or
global machine changes; repo private and inherited Actions disabled.
