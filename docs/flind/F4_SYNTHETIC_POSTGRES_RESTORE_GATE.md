# Flind synthetic PostgreSQL backup and restore gate

Status: **test implementation pending exact-commit GitHub CI**. This gate does
not establish production disaster recovery or a public Flind release.

## Why

A successful database migration and its idempotent rerun do not prove that a
backup can be restored. The first release must have a separate **restore**
acceptance record, rather than treating migration checks as backup evidence.

## Behavior

On an explicit `postgres_restore=true` manual run of
`.github/workflows/flind-runtime-migrations.yml`, or a push to an isolated
`flind-ci/postgres-recovery-*` branch, the workflow:

1. Checks all synthetic-only environment guards before invoking Docker.
2. Runs the real PostgreSQL, Kafka, ClickHouse, Redis and migrations stack.
3. Inserts three non-sensitive synthetic records in a fresh, throwaway
   public-schema table; refuses to operate if the proof table or restore
   database already exists.
4. Makes an actual PostgreSQL **custom-format full database backup**, verifies
   its table-of-contents is readable and restores it with
   `--single-transaction --exit-on-error` into a separate newly created DB.
5. Compares exact restored synthetic rows and the full list of public-schema
   relation names/kinds. An intentionally tampered restored tenant row must
   fail the row comparison, then a correction must restore equality.
6. Prints only sizes, hashes and outcome to GitHub job summary; does not
   upload a database backup or use any production connection.
7. Removes the synthetic table, restore database and ephemeral backup
   directory on exit, whether the test passes or fails.

The script refuses to run except on an ephemeral GitHub Actions runner,
with the expected throwaway dev database URL, `DEBUG=1`, exact evidence
location and pinned Postgres 15 server. It does not create, overwrite or
delete user databases, and does not use local Windows disk storage.

## Reproduction

Use the existing migration workflow's manual `postgres_restore` input,
or an isolated `flind-ci/postgres-recovery-*` branch. The local
`python3 -m unittest tools.flind.test_qualify_postgres_backup_restore_synthetic -v`
and `bash -n tools/flind/qualify_postgres_backup_restore_synthetic.sh`
verify source syntax and fail-closed preconditions without connecting to
any database. They do **not** qualify an actual restore.

## Important limitations

- Only the **synthetic** PostgreSQL 15 dev database and proof records are
  restored. This is not a real customer-data or production retention test.
- The public-schema catalog check compares relation names and kinds,
  not every function body, index expression, grant or all migrated rows.
- No ClickHouse, Kafka stream, object storage, encryption-key or full
  cross-service consistent snapshot/restore is verified.
- No recovery point objective (RPO), recovery time objective (RTO),
  backup encryption, offsite storage, upgrade with pre-existing real data,
  or disaster drill is established.
- Final status stays **NO-GO** until all release gates pass, rights/provenance
  are verified, and the owner explicitly authorizes `GREEN LIGHT FLIND`.
