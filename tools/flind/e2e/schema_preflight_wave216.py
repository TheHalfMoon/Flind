#!/usr/bin/env python3
"""Read-only original Flind E2E database schema admission gate."""
import json
import subprocess
import sys

from tools.flind.e2e.verify_wave216 import (
    SERVICES, assert_owned_service, check_clickhouse, check_redis,
    clickhouse_sql, inspect, read_database_names,
)

POSTGRES_REQUIRED = {"posthog_cohort", "posthog_team", "posthog_user", "posthog_organization"}
CLICKHOUSE_REQUIRED = {
    "sharded_events", "person", "person_distinct_id", "events_dead_letter_queue"
}

def missing_tables(required, actual):
    return sorted(required.difference(actual))

def postgres_tables():
    query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    r = subprocess.run(
        ["docker", "exec", "flindwave216-postgres-1",
         "psql", "-U", "flind_test", "-d", "test_posthog", "-tAc", query],
        capture_output=True, text=True, timeout=20, check=True)
    return set(r.stdout.splitlines())

def clickhouse_tables():
    query = "SELECT name FROM system.tables WHERE database = 'flind_test_wave216abc123' FORMAT TSV"
    return set(clickhouse_sql(query).splitlines())

def preflight():
    for service in SERVICES:
        assert_owned_service(service, inspect(service))
    read_database_names()
    check_redis()
    check_clickhouse()
    missing_pg = missing_tables(POSTGRES_REQUIRED, postgres_tables())
    missing_ch = missing_tables(CLICKHOUSE_REQUIRED, clickhouse_tables())
    return {
        "phase": "wave216_original_service_schema_preflight",
        "original_postgres_schema_ready": not missing_pg,
        "original_clickhouse_schema_ready": not missing_ch,
        "missing_postgres_tables": missing_pg,
        "missing_clickhouse_tables": missing_ch,
        "original_node_service_e2e_qualified": False,
        "release_qualified": False,
    }

if __name__ == "__main__":
    try:
        evidence = preflight()
        print(json.dumps(evidence, indent=2, sort_keys=True))
        sys.exit(0 if evidence["original_postgres_schema_ready"] and
                 evidence["original_clickhouse_schema_ready"] else 2)
    except Exception as exc:
        print("FLIND_WAVE216_SCHEMA_REFUSED " + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
