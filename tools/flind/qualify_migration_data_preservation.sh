#!/usr/bin/env bash
# Synthetic migration idempotency canary for runner-local PostgreSQL and ClickHouse.
# Intended ONLY for the ephemeral real-service Flind migration CI workflow.
set -euo pipefail
fail() { printf 'Flind migration preservation: %s\n' "$*" >&2; exit 2; }
[[ "$#" == '1' && ( "$1" == 'seed' || "$1" == 'verify' ) ]] || fail 'expected seed or verify'
mode="$1"
[[ "${GITHUB_ACTIONS:-}" == 'true' ]] || fail 'ephemeral GitHub runner required'
[[ "${FLIND_SYNTHETIC_MIGRATION_CHECK:-}" == '1' ]] || fail 'explicit synthetic opt-in required'
[[ "${DATABASE_URL:-}" == 'postgres://posthog:posthog@localhost:5432/posthog' ]] || fail 'unexpected Postgres URL'
[[ "${CLICKHOUSE_DATABASE:-}" == 'posthog' && "${CLICKHOUSE_HOST:-}" == 'localhost' ]] || fail 'unexpected ClickHouse target'
[[ "${DEBUG:-}" == '1' ]] || fail 'dev-only context required'
[[ -n "${GITHUB_WORKSPACE:-}" && "${EVIDENCE:-}" == "$GITHUB_WORKSPACE/flind-evidence" ]] || fail 'unexpected evidence location'
[[ "$(pwd -P)" == "$GITHUB_WORKSPACE" && -f docker-compose.dev.yml ]] || fail 'expected checked-out Flind root'

pg="$(docker compose -f docker-compose.dev.yml ps -q db)"
ch="$(docker compose -f docker-compose.dev.yml ps -q clickhouse)"
[[ "$pg" =~ ^[a-f0-9]{12,64}$ && "$ch" =~ ^[a-f0-9]{12,64}$ ]] || fail 'expected isolated compose database containers'
psql_db() { docker exec "$pg" psql -X -A -t -v ON_ERROR_STOP=1 -U posthog -d posthog -c "$1"; }
ch_query() { docker exec "$ch" clickhouse-client --query "$1"; }
pg_version="$(psql_db 'SHOW server_version_num')"
[[ "$pg_version" =~ ^[0-9]+$ && "$pg_version" -ge 150000 && "$pg_version" -lt 160000 ]] || fail 'unexpected synthetic Postgres major version'

pg_table="public.flind_ci_migration_preservation"
ch_table="posthog.flind_ci_migration_preservation"
pg_rows="COPY (SELECT tenant_id,marker,sample_count FROM $pg_table ORDER BY tenant_id) TO STDOUT WITH CSV"
ch_rows="SELECT tenant_id,marker,sample_count FROM $ch_table ORDER BY tenant_id FORMAT TSV"
pg_before="$EVIDENCE/migration-canary-pg-before.csv"
ch_before="$EVIDENCE/migration-canary-clickhouse-before.tsv"

if [[ "$mode" == 'seed' ]]; then
    [[ -d "$EVIDENCE" && ! -e "$pg_before" && ! -e "$ch_before" ]] || fail 'unexpected or preexisting baseline'
    [[ "$(psql_db "SELECT to_regclass('$pg_table') IS NULL")" == 't' ]] || fail 'Postgres proof table already exists'
    [[ "$(ch_query "SELECT count() FROM system.tables WHERE database='posthog' AND name='flind_ci_migration_preservation'")" == '0' ]] || fail 'ClickHouse proof table already exists'
    psql_db "CREATE TABLE $pg_table (tenant_id integer PRIMARY KEY, marker text NOT NULL, sample_count integer NOT NULL)" >/dev/null
    psql_db "INSERT INTO $pg_table VALUES (101,'local-tenant-one',7),(202,'local-tenant-two',13)" >/dev/null
    ch_query "CREATE TABLE $ch_table (tenant_id UInt32, marker String, sample_count UInt32) ENGINE=MergeTree ORDER BY tenant_id"
    ch_query "INSERT INTO $ch_table VALUES (101,'local-tenant-one',7),(202,'local-tenant-two',13)"
    psql_db "$pg_rows" > "$pg_before"
    ch_query "$ch_rows" > "$ch_before"
    [[ "$(wc -l < "$pg_before")" -eq 2 && "$(wc -l < "$ch_before")" -eq 2 ]] || fail 'expected exactly two tenant markers per database'
    grep -q '^101,local-tenant-one,7$' "$pg_before" || fail 'Postgres tenant-one baseline mismatch'
    grep -q '^202,local-tenant-two,13$' "$pg_before" || fail 'Postgres tenant-two baseline mismatch'
    grep -q $'^101\tlocal-tenant-one\t7$' "$ch_before" || fail 'ClickHouse tenant-one baseline mismatch'
    grep -q $'^202\tlocal-tenant-two\t13$' "$ch_before" || fail 'ClickHouse tenant-two baseline mismatch'
    echo 'synthetic_persistence_markers_seeded=pass'
else
    [[ -s "$pg_before" && -s "$ch_before" ]] || fail 'missing seeded baseline'
    pg_after="$EVIDENCE/migration-canary-pg-after.csv"
    ch_after="$EVIDENCE/migration-canary-clickhouse-after.tsv"
    psql_db "$pg_rows" > "$pg_after"
    ch_query "$ch_rows" > "$ch_after"
    cmp -s "$pg_before" "$pg_after" || fail 'Postgres synthetic tenant records changed during rerun'
    cmp -s "$ch_before" "$ch_after" || fail 'ClickHouse synthetic tenant records changed during rerun'
    [[ "$(wc -l < "$pg_after")" -eq 2 && "$(wc -l < "$ch_after")" -eq 2 ]] || fail 'unexpected tenant count after migrations'

    # Live negative control: mutate only a synthetic PostgreSQL row and prove
    # the same comparator rejects it, then restore exactly the original value.
    psql_db "UPDATE $pg_table SET marker='intentionally-tampered' WHERE tenant_id=202" >/dev/null
    [[ "$(psql_db "SELECT marker FROM $pg_table WHERE tenant_id=202")" == 'intentionally-tampered' ]] || fail 'Postgres test mutation was not applied'
    psql_db "$pg_rows" > "$EVIDENCE/migration-canary-pg-tampered.csv"
    if cmp -s "$pg_before" "$EVIDENCE/migration-canary-pg-tampered.csv"; then
        fail 'Postgres comparator did not detect a modified tenant record'
    fi
    psql_db "UPDATE $pg_table SET marker='local-tenant-two' WHERE tenant_id=202" >/dev/null
    psql_db "$pg_rows" > "$EVIDENCE/migration-canary-pg-repaired.csv"
    cmp -s "$pg_before" "$EVIDENCE/migration-canary-pg-repaired.csv" || fail 'Postgres record did not recover after negative control'

    # Live negative control: remove a synthetic ClickHouse tenant row from this
    # disposable table only, require a failed comparison, then restore it.
    ch_query "TRUNCATE TABLE $ch_table"
    ch_query "INSERT INTO $ch_table VALUES (101,'local-tenant-one',7)"
    ch_query "$ch_rows" > "$EVIDENCE/migration-canary-clickhouse-tampered.tsv"
    [[ "$(wc -l < "$EVIDENCE/migration-canary-clickhouse-tampered.tsv")" -eq 1 ]] || fail 'ClickHouse test row deletion was not applied'
    if cmp -s "$ch_before" "$EVIDENCE/migration-canary-clickhouse-tampered.tsv"; then
        fail 'ClickHouse comparator did not detect a deleted tenant record'
    fi
    ch_query "INSERT INTO $ch_table VALUES (202,'local-tenant-two',13)"
    ch_query "$ch_rows" > "$EVIDENCE/migration-canary-clickhouse-repaired.tsv"
    cmp -s "$ch_before" "$EVIDENCE/migration-canary-clickhouse-repaired.tsv" || fail 'ClickHouse records did not recover after negative control'

    psql_db "DROP TABLE $pg_table" >/dev/null
    ch_query "DROP TABLE $ch_table"
    {
        echo 'synthetic_migration_data_preserved=pass'
        echo 'datastores=postgres,clickhouse'
        echo 'tenants=2'
        echo 'postgres_modified_row_negative_control=pass'
        echo 'clickhouse_deleted_row_negative_control=pass'
        echo 'post_negative_control_repair_parity=pass'
        echo "postgres_snapshot_sha256=$(sha256sum "$pg_before" | cut -d' ' -f1)"
        echo "clickhouse_snapshot_sha256=$(sha256sum "$ch_before" | cut -d' ' -f1)"
        echo 'upgrade_from_prior_release_qualified=false'
        echo 'production_data_qualified=false'
    } > "$EVIDENCE/migration-canary-summary.txt"
    cat "$EVIDENCE/migration-canary-summary.txt"
fi
