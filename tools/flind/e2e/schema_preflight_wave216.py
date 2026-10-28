#!/usr/bin/env python3
"""Fail-closed original Flind E2E schema preflight; not release qualification."""
import json
from pathlib import Path
import re
import subprocess
import sys
from tools.flind.e2e.verify_wave216 import (
    SERVICES, assert_owned_service, check_clickhouse, check_redis,
    clickhouse_sql, inspect, read_database_names,
)

ROOT = Path(__file__).resolve().parents[3]
SQL_HELPER = ROOT / "nodejs/tests/helpers/sql.ts"
CH_HELPER = ROOT / "nodejs/tests/helpers/clickhouse.ts"
COMMON_DB = "test_posthog"
PERSONS_DB = "test_persons"
POSTGRES_REQUIRED = frozenset({
    "posthog_cohort", "posthog_featureflag", "posthog_organizationmembership",
    "posthog_project", "posthog_organization", "posthog_action",
    "posthog_user", "posthog_team",
})
PERSONS_REQUIRED = frozenset({
    "posthog_grouptypemapping", "posthog_group",
    "posthog_featureflaghashkeyoverride", "posthog_cohortpeople",
    "posthog_flatpersonoverride", "posthog_pendingpersonoverride",
    "posthog_personoverride", "posthog_personoverridemapping",
    "posthog_persondistinctid", "posthog_person",
})
CLICKHOUSE_REQUIRED = frozenset({
    "sharded_events", "person", "person_distinct_id", "person_distinct_id2",
    "person_distinct_id_overrides", "person_static_cohort",
    "sharded_session_replay_events", "events_dead_letter_queue",
    "groups", "ingestion_warnings", "sharded_ingestion_warnings",
    "sharded_app_metrics", "ingestion_warnings_v2",
})


def missing_tables(required, actual):
    return sorted(set(required).difference(actual))


def _source_segment(file, start, end):
    if not file.is_file() or file.is_symlink():
        raise ValueError("original E2E source unavailable")
    content = file.read_text(encoding="utf-8")
    if content.count(start) != 1:
        raise ValueError("original E2E source anchor ambiguous")
    segment = content.split(start, 1)[1]
    if end not in segment:
        raise ValueError("original E2E source boundary missing")
    return segment.split(end, 1)[0]


def validate_original_reset_contract():
    """Never authorize destructive Jest after source reset tables drift."""
    pg_common = _source_segment(
        SQL_HELPER, "export const POSTGRES_DELETE_COMMON_TABLES_QUERY = " + chr(96), chr(96)
    )
    pg_persons = _source_segment(
        SQL_HELPER, "export const POSTGRES_DELETE_PERSONS_TABLES_QUERY = " + chr(96), chr(96)
    )
    ch_reset = _source_segment(
        CH_HELPER, "    async resetTestDatabase(): Promise<void> {",
        "    // Topics that this database",
    )
    pg_pattern = r"(?m)^\s*DELETE FROM (posthog_[a-z0-9_]+) CASCADE;"
    ch_pattern = r"this\.truncate\('([a-z0-9_]+)'\)"
    for extracted, required in (
        (re.findall(pg_pattern, pg_common), POSTGRES_REQUIRED),
        (re.findall(pg_pattern, pg_persons), PERSONS_REQUIRED),
        (re.findall(ch_pattern, ch_reset), CLICKHOUSE_REQUIRED),
    ):
        if len(extracted) != len(required) or set(extracted) != required:
            raise ValueError("first-party reset table contract changed")
    return True


def postgres_tables(database=COMMON_DB):
    if database not in (COMMON_DB, PERSONS_DB):
        raise ValueError("refusing non-owned PostgreSQL database")
    query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    r = subprocess.run(
        ["docker", "exec", "flindwave216-postgres-1", "psql", "-X",
         "-v", "ON_ERROR_STOP=1", "-U", "flind_test", "-d", database,
         "-tAc", query],
        capture_output=True, text=True, timeout=20, check=True,
    )
    return set(r.stdout.splitlines())


def postgres_migration_count():
    r = subprocess.run(
        ["docker", "exec", "flindwave216-postgres-1", "psql", "-X",
         "-v", "ON_ERROR_STOP=1", "-U", "flind_test", "-d", COMMON_DB,
         "-tAc", "SELECT count(*) FROM django_migrations"],
        capture_output=True, text=True, timeout=20, check=True,
    )
    count = int(r.stdout.strip())
    if count < 0:
        raise ValueError("invalid Django migration count")
    return count


def clickhouse_tables():
    return set(clickhouse_sql(
        "SELECT name FROM system.tables "
        "WHERE database = 'flind_test_wave216abc123' FORMAT TSV"
    ).splitlines())


def clickhouse_kafka_engine_count():
    return int(clickhouse_sql(
        "SELECT count() FROM system.tables "
        "WHERE database = 'flind_test_wave216abc123' AND engine = 'Kafka'"
    ))


def preflight():
    # No DB probe at all when first-party reset contract has changed.
    validate_original_reset_contract()
    for service in SERVICES:
        assert_owned_service(service, inspect(service))
    read_database_names()
    check_redis()
    check_clickhouse()
    common = postgres_tables(COMMON_DB)
    persons = postgres_tables(PERSONS_DB)
    ch = clickhouse_tables()
    missing_common = missing_tables(POSTGRES_REQUIRED, common)
    missing_persons = missing_tables(PERSONS_REQUIRED, persons)
    missing_ch = missing_tables(CLICKHOUSE_REQUIRED, ch)
    migration_count = postgres_migration_count() if "django_migrations" in common else 0
    kafka_count = clickhouse_kafka_engine_count()
    pg_ready = not missing_common and not missing_persons and migration_count > 0
    ch_ready = not missing_ch and kafka_count > 0
    return {
        "phase": "wave218_original_service_reset_contract_preflight",
        "original_reset_contract_matches_source": True,
        "original_postgres_schema_ready": pg_ready,
        "original_clickhouse_schema_ready": ch_ready,
        "missing_postgres_tables": missing_common,
        "missing_persons_tables": missing_persons,
        "missing_clickhouse_tables": missing_ch,
        "common_django_migration_rows_present": migration_count > 0,
        "clickhouse_kafka_engine_present": kafka_count > 0,
        "schema_preconditions_passed": pg_ready and ch_ready,
        "full_migration_graph_qualified": False,
        "original_node_service_e2e_qualified": False,
        "release_qualified": False,
    }


if __name__ == "__main__":
    try:
        evidence = preflight()
        print(json.dumps(evidence, indent=2, sort_keys=True))
        sys.exit(0 if evidence["schema_preconditions_passed"] else 2)
    except Exception as exc:
        print("FLIND_WAVE218_SCHEMA_REFUSED " + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
