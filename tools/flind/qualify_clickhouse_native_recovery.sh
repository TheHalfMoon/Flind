#!/usr/bin/env bash
# Synthetic ClickHouse Native-format export/import proof, not a production backup.
set -euo pipefail

fail() { printf 'Flind ClickHouse recovery: %s\n' "$*" >&2; exit 2; }
[[ "${GITHUB_ACTIONS:-}" == 'true' ]] || fail 'ephemeral GitHub runner required'
[[ "${FLIND_SYNTHETIC_CLICKHOUSE_RECOVERY:-}" == '1' ]] || fail 'explicit synthetic opt-in required'
[[ "${CLICKHOUSE_HOST:-}" == 'localhost' && "${CLICKHOUSE_DATABASE:-}" == 'posthog' ]] || fail 'unexpected ClickHouse target'
[[ "${DATABASE_URL:-}" == 'postgres://posthog:posthog@localhost:5432/posthog' ]] || fail 'unexpected companion Postgres URL'
[[ "${DEBUG:-}" == '1' ]] || fail 'development testing context required'
[[ -n "${GITHUB_WORKSPACE:-}" && "${EVIDENCE:-}" == "$GITHUB_WORKSPACE/flind-evidence" ]] || fail 'unexpected evidence location'
[[ -n "${RUNNER_TEMP:-}" && -d "$RUNNER_TEMP" ]] || fail 'ephemeral temp required'
[[ "$(pwd -P)" == "$GITHUB_WORKSPACE" && -f docker-compose.dev.yml ]] || fail 'expected checked-out Flind repository'

ch="$(docker compose -f docker-compose.dev.yml ps -q clickhouse)"
[[ "$ch" =~ ^[a-f0-9]{12,64}$ ]] || fail 'expected isolated compose ClickHouse'
ch_query() { docker exec "$ch" clickhouse-client --query "$1"; }
version="$(ch_query "SELECT version()")"
[[ "$version" == 26.* ]] || fail 'expected pinned synthetic ClickHouse 26'

src='posthog.flind_ci_native_recovery_source'
dst='posthog.flind_ci_native_recovery_restored'
[[ "$(ch_query "SELECT count() FROM system.tables WHERE database='posthog' AND name IN ('flind_ci_native_recovery_source','flind_ci_native_recovery_restored')")" == '0' ]] || fail 'synthetic tables already exist'
work="$(mktemp -d "$RUNNER_TEMP/flind-ch-native.XXXXXXXX")"
source_created=0
restored_created=0
cleanup() {
    local status=$?
    trap - EXIT
    if [[ "$restored_created" == '1' ]]; then
        if ! ch_query "DROP TABLE IF EXISTS $dst SYNC" >/dev/null 2>&1; then
            printf 'Flind ClickHouse recovery: unable to drop restored test table\n' >&2
            status=3
        fi
    fi
    if [[ "$source_created" == '1' ]]; then
        if ! ch_query "DROP TABLE IF EXISTS $src SYNC" >/dev/null 2>&1; then
            printf 'Flind ClickHouse recovery: unable to drop source test table\n' >&2
            status=3
        fi
    fi
    if ! rm -rf -- "$work"; then
        printf 'Flind ClickHouse recovery: unable to remove ephemeral archive\n' >&2
        status=3
    fi
    exit "$status"
}
trap cleanup EXIT

schema='(tenant_id UInt32, marker String, sample_count UInt32) ENGINE=MergeTree ORDER BY tenant_id'
ch_query "CREATE TABLE $src $schema"
source_created=1
ch_query "INSERT INTO $src VALUES (101,'first-synthetic-tenant',7),(202,'second-synthetic-tenant',13),(303,'third-synthetic-tenant',27)"
rows="SELECT tenant_id,marker,sample_count FROM"
ch_query "$rows $src ORDER BY tenant_id FORMAT TSV" > "$work/source.tsv"
[[ "$(wc -l < "$work/source.tsv")" -eq 3 ]] || fail 'expected three source rows'
docker exec "$ch" clickhouse-client --query "$rows $src ORDER BY tenant_id FORMAT Native" > "$work/canary.native"
[[ -s "$work/canary.native" ]] || fail 'empty Native export'
ch_query "CREATE TABLE $dst $schema"
restored_created=1
docker exec -i "$ch" clickhouse-client --query "INSERT INTO $dst FORMAT Native" < "$work/canary.native"
ch_query "$rows $dst ORDER BY tenant_id FORMAT TSV" > "$work/restored.tsv"
cmp -s "$work/source.tsv" "$work/restored.tsv" || fail 'Native import changed synthetic tenant rows'

# A negative control must detect an extra synthetic row in the restored table.
ch_query "INSERT INTO $dst VALUES (999,'intentional-tamper',999)"
ch_query "$rows $dst ORDER BY tenant_id FORMAT TSV" > "$work/tampered.tsv"
if cmp -s "$work/source.tsv" "$work/tampered.tsv"; then
    fail 'negative control did not detect changed records'
fi
ch_query "TRUNCATE TABLE $dst"
docker exec -i "$ch" clickhouse-client --query "INSERT INTO $dst FORMAT Native" < "$work/canary.native"
ch_query "$rows $dst ORDER BY tenant_id FORMAT TSV" > "$work/reimported.tsv"
cmp -s "$work/source.tsv" "$work/reimported.tsv" || fail 'reimport after tampering did not restore parity'

mkdir -p "$EVIDENCE"
{
    printf 'synthetic_clickhouse_native_export_import=pass\n'
    printf 'clickhouse_major=26\n'
    printf 'synthetic_tenants=3\n'
    printf 'negative_control_detected=true\n'
    printf 'archive_bytes=%s\n' "$(wc -c < "$work/canary.native" | tr -d '[:space:]')"
    printf 'archive_sha256=%s\n' "$(sha256sum "$work/canary.native" | cut -d' ' -f1)"
    printf 'full_clickhouse_backup_qualified=false\n'
    printf 'production_restore_qualified=false\n'
    printf 'cross_service_restore_qualified=false\n'
} > "$EVIDENCE/clickhouse-native-recovery.txt"
cat "$EVIDENCE/clickhouse-native-recovery.txt"
