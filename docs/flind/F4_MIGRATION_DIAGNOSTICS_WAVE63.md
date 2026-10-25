# Wave 63 — Inspectable, fail-closed Django migration frontier

## Blocker addressed

Wave 55–57 showed real forward migration progress on a disposable
PostgreSQL 17 cluster, but a timed-out Django command exposed only a
committed-row count. Even a failed round with zero committed rows could
not distinguish a slow Django startup from the migration currently
executing. Blind retries repeatedly discard temporary test databases.

Wave 63 adds **sanitized execution-stage evidence**, without weakening
any database, credential, process, timeout or disk boundary:

- Unbuffer Python's actual `manage.py migrate` stdout with `python -u`.
- Request Django's regular migration progress messages with verbosity 1.
- Parse **only** fixed-format `Applying app.migration... [OK]` lines.
  Return last attempted, last console-completed, and interrupted
  migration labels. A line with arbitrary suffix text cannot match.
- Include only Boolean flags for whether Django wrote output and reached
  the `Running migrations:` stage.
- Include an allowlisted exception **class**, never its message, SQL,
  environment, access tokens, stdout/stderr or database URL.
- Attach the same receipts to each resumable migration round.
- Preserve the original PostgreSQL recorder as the independent
  source of truth for **committed** migrations. A console `OK` alone
  cannot grant full-schema qualification.
- The existing disk floor, process group termination, private random
  loopback endpoint, transient credentials and no-deploy restrictions
  remain unchanged.

## How to reproduce

Use the full Flind checkout and locked Python 3.14.7 runtime with 201/201
applicable direct dependencies. Commands must run only in a machine
permitted to start a disposable, authenticated PostgreSQL cluster.

```sh
python -m unittest \
  tools.flind.test_migration_diagnostics_wave63 \
  tools.flind.test_isolated_migrations_wave55 \
  tools.flind.test_resumable_migrations_wave57 -q

python -m tools.flind.qualify_resumable_migrations_wave57 \
  --json --rounds 1 --seconds 120
```

If a private ephemeral schema is not applied to completion, the script
exits unsuccessfully; it must never be treated as a launch pass.

## Real evidence and remaining conditions

- As of October 25, 2026, the full locked Python dependency audit
  passed: 201/201 applicable direct dependencies, zero mismatches.
- A bounded, previously uninstrumented real attempt on a disposable
  PostgreSQL 17 cluster returned **zero committed migration rows in 120
  seconds**, stopped without retrying and removed the test database.
  `isolated_postgres_passed=true` and
  `full_schema_migrations_completed=false`.
- Focused diagnostic and Wave 55/57 safety tests: 21/21 PASS.
- Additional instrumented live qualification receipts are separate from
  source tests and are recorded only if actually observed.
- Full schema, end-to-end authenticated capture, ClickHouse query
  readback, tenant isolation and browser/device flows remain pending.
- Repository stays private, inherited GitHub Actions disabled,
  mandatory source attribution retained, no paid services, publication
  or deployment.

## Instrumented PostgreSQL execution evidence (October 25, 2026)

A **real** bounded 120-second migration pass, using the full exact
Python dependency lock and one disposable, localhost SCRAM-protected
PostgreSQL 17 cluster, returned:

- PostgreSQL probe: PASS.
- Committed `django_migrations` rows: **2,383** (not a full pass).
- Last independently committed row:
  `experiments.0037_squash_2026_09_07_finalize_fks`.
- Last Django console attempt, interrupted at the bounded timeout:
  `error_tracking.0001_squash_2026_09_07_initial`.
- `django_console_output_seen=true`,
  `django_migration_stage_seen=true`, no recognized exception class.
- `full_schema_migrations_completed=false`,
  `release_qualified=false`.
- All private test database resources were terminated and removed.

The interrupted migration label identifies the **location of a timed
attempt**, not proof the migration is defective. The first attempt
was stopped by the configured 120s guard before receiving Django
process exit success. Retrying must preserve normal migration recorder
semantics without `--fake`, unauthorized data sources, or SQL shortcuts.

Test evidence:
- Diagnostic/safety suites in the Wave 63 worktree: **21/21 PASS**.
- Complete existing Python regression tests on the untouched full
  working-tree checkout: **442/442 PASS**. The latter excludes new
  Wave 63 tests, which were run separately against the edited files.
