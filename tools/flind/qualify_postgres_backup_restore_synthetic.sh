#!/usr/bin/env bash
# Synthetic-only Flind Postgres recovery smoke. Intended for an ephemeral GitHub
# Actions runner AFTER real Django/persons/ClickHouse migrations have completed.
# This is NOT a production backup procedure and never accepts real DB settings.
set -euo pipefail

fail() { printf 'Flind synthetic PG restore: %s\n' "$*" >&2; exit 2; }

[[ "${GITHUB_ACTIONS:-}" == 'true' ]] || fail 'GitHub Actions ephemeral runner required'
[[ "${FLIND_SYNTHETIC_PG_RESTORE:-}" == '1' ]] || fail 'explicit synthetic opt-in required'
[[ "${DATABASE_URL:-}" == 'postgres://posthog:posthog@localhost:5432/posthog' ]] || fail 'unexpected database URL; refusing to touch it'
[[ "${DEBUG:-}" == '1' ]] || fail 'development testing context required'
[[ -n "${GITHUB_WORKSPACE:-}" && "${EVIDENCE:-}" == "${GITHUB_WORKSPACE}/flind-evidence" ]] || fail 'unexpected evidence destination'
[[ -n "${RUNNER_TEMP:-}" && -d "$RUNNER_TEMP" ]] || fail 'ephemeral runner temp directory required'
[[ "$(pwd -P)" == "$GITHUB_WORKSPACE" && -f docker-compose.dev.yml ]] || fail 'run from checked-out Flind repository root'

db="$(docker compose -f docker-compose.dev.yml ps -q db)"
[[ "$db" =~ ^[a-f0-9]{12,64}$ ]] || fail 'expected one running compose db container'
psql_db() { docker exec "$db" psql -X -v ON_ERROR_STOP=1 -At -U posthog -d "$1" -c "$2"; }
version="$(psql_db posthog 'SHOW server_version_num')"
[[ "$version" =~ ^[0-9]+$ && "$version" -ge 150000 && "$version" -lt 160000 ]] || fail 'expected pinned synthetic Postgres 15 server'
[[ "$(psql_db postgres "SELECT count(*) FROM pg_database WHERE datname='flind_restore_verify'")" == '0' ]] || fail 'verification DB already exists'
[[ "$(psql_db posthog "SELECT to_regclass('public.flind_backup_restore_proof') IS NULL")" == 't' ]] || fail 'proof table already exists'

work="$(mktemp -d "$RUNNER_TEMP/flind-pg-restore.XXXXXXXX")"
created_proof=0
created_database=0
cleanup() {
    local status=$?
    trap - EXIT
    if [[ "$created_database" == '1' ]]; then
        if ! docker exec "$db" dropdb -U posthog flind_restore_verify >/dev/null 2>&1; then
            printf 'Flind synthetic PG restore: failed to remove test database\n' >&2
            status=3
        fi
    fi
    if [[ "$created_proof" == '1' ]]; then
        if ! psql_db posthog 'DROP TABLE public.flind_backup_restore_proof' >/dev/null 2>&1; then
            printf 'Flind synthetic PG restore: failed to remove proof table\n' >&2
            status=3
        fi
    fi
    if ! rm -rf -- "$work"; then
        printf 'Flind synthetic PG restore: failed to remove ephemeral archive\n' >&2
        status=3
    fi
    exit "$status"
}
trap cleanup EXIT

psql_db posthog "CREATE TABLE public.flind_backup_restore_proof (
    id integer PRIMARY KEY, team_id integer NOT NULL,
    marker text NOT NULL, active boolean NOT NULL
)" >/dev/null
created_proof=1
psql_db posthog "INSERT INTO public.flind_backup_restore_proof VALUES
    (1,101,'flind-local-only',true),
    (2,202,'second-synthetic-team',false),
    (3,101,'restore-repeat-proof',true)" >/dev/null

docker exec "$db" pg_dump --format=custom --no-owner --no-acl -U posthog -d posthog > "$work/synthetic-full-postgres.dump"
[[ -s "$work/synthetic-full-postgres.dump" ]] || fail 'empty backup'
docker exec -i "$db" pg_restore --list < "$work/synthetic-full-postgres.dump" > "$work/backup-toc.txt"
[[ -s "$work/backup-toc.txt" ]] || fail 'unreadable backup TOC'

docker exec "$db" createdb -U posthog flind_restore_verify
created_database=1
docker exec -i "$db" pg_restore --exit-on-error --single-transaction --no-owner --no-acl \
    -U posthog -d flind_restore_verify < "$work/synthetic-full-postgres.dump"

rows_sql="COPY (SELECT id,team_id,marker,active FROM public.flind_backup_restore_proof ORDER BY id) TO STDOUT WITH CSV"
schema_sql="COPY (SELECT c.relkind::text || '|' || c.relname
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' ORDER BY c.relkind,c.relname) TO STDOUT WITH CSV"
psql_db posthog "$rows_sql" > "$work/source-rows.csv"
psql_db flind_restore_verify "$rows_sql" > "$work/restored-rows.csv"
[[ "$(wc -l < "$work/source-rows.csv")" -eq 3 ]] || fail 'expected three synthetic rows'
cmp -s "$work/source-rows.csv" "$work/restored-rows.csv" || fail 'restored synthetic rows differ'

psql_db posthog "$schema_sql" > "$work/source-schema.csv"
psql_db flind_restore_verify "$schema_sql" > "$work/restored-schema.csv"
[[ "$(wc -l < "$work/source-schema.csv")" -ge 10 ]] || fail 'unexpectedly small migrated PostgreSQL schema'
cmp -s "$work/source-schema.csv" "$work/restored-schema.csv" || fail 'public schema relation names/kinds differ'

# Negative control proves the comparison detects a changed tenant's data.
psql_db flind_restore_verify "UPDATE public.flind_backup_restore_proof
    SET marker='TAMPERED' WHERE id=2" >/dev/null
psql_db flind_restore_verify "$rows_sql" > "$work/tampered-rows.csv"
if cmp -s "$work/source-rows.csv" "$work/tampered-rows.csv"; then
    fail 'negative control did not detect tampering'
fi
psql_db flind_restore_verify "UPDATE public.flind_backup_restore_proof
    SET marker='second-synthetic-team' WHERE id=2" >/dev/null
psql_db flind_restore_verify "$rows_sql" > "$work/restored-rows-final.csv"
cmp -s "$work/source-rows.csv" "$work/restored-rows-final.csv" || fail 'restored test data did not recover after tamper rollback'

mkdir -p "$EVIDENCE"
{
    printf 'synthetic_pg_backup_restore=pass\n'
    printf 'source_pg_major=15\n'
    printf 'synthetic_rows=3\n'
    printf 'schema_relations=%s\n' "$(wc -l < "$work/source-schema.csv" | tr -d '[:space:]')"
    printf 'negative_control_tamper_detected=true\n'
    printf 'archive_bytes=%s\n' "$(wc -c < "$work/synthetic-full-postgres.dump" | tr -d '[:space:]')"
    printf 'archive_sha256=%s\n' "$(sha256sum "$work/synthetic-full-postgres.dump" | cut -d' ' -f1)"
    printf 'production_backup_qualified=false\n'
    printf 'clickhouse_restore_qualified=false\n'
} > "$EVIDENCE/postgres-restore-smoke.txt"
cat "$EVIDENCE/postgres-restore-smoke.txt"
