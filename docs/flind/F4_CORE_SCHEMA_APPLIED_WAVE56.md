# Wave 56 — Successfully apply real scoped Django migrations

## Background

The real full Flind schema migration in Wave 55 persisted 2,541 and
2,610 migration rows in independent, disposable attempts before their
time guards stopped the processes. It never reached a qualified full
exit. Repeating large migrations against the shared machine database
is prohibited.

This wave demonstrates actual migration execution and SQL readback
rather than only framework imports and showmigrations --plan.

## Implementation

- Add an explicit allowlisted contenttypes app-label argument to the
  existing private migrations probe. The default full-schema behavior
  remains unchanged. Arbitrary app names are rejected.
- Add tools/flind/qualify_core_schema_wave56.py, which first verifies
  the frozen Python direct dependency lock and then initializes a
  separately authenticated temporary PostgreSQL 17 cluster.
- Run real Django migrate contenttypes --noinput, with the Wave 55
  bounded disk/time controls and isolated environment.
- Require both a successful migration command and a PostgreSQL SQL
  receipt: at least two contenttypes migration records and existence
  of public.django_content_type.
- Destroy all test schema/data with the temporary cluster after the
  receipt is collected. No changes to the global Postgres instance.

## Actual macbook evidence, October 25, 2026

- Python 3.14.7 direct lock: 201/201 exact distributions.
- Isolated PostgreSQL 17 test DB: PASS.
- Scoped Django contenttypes schema migrations: PASS.
- Two migration records committed and django_content_type confirmed by SQL.
- No unfinished subprocesses or temporary cluster left after the run.
- Focused source tests 14/14 PASS; full Flind Python suite 430/430 PASS.
- core_schema_qualified=true; full_schema_qualified=false;
  release_qualified=false.

Reproduce using the locked, separate Python runtime:

    python tools/flind/qualify_core_schema_wave56.py --json

## Remaining release work

Contenttypes is only a small framework schema segment, not the Flind
analytics/auth product. Full migrations, workers/Kafka, SDK ingest,
ClickHouse readback, OAuth and tenant isolation, security/staticfiles
warnings and device/browser E2E must still pass. An allowlisted scoped
migration is intentionally not permission to skip or fake the
remaining inherited migrations.

No publication or deployment. Repository private, Actions disabled,
required legal source notices preserved.
