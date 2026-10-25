#!/usr/bin/env python3
"""Real isolated PostgreSQL + Redis + ClickHouse service overlap with scoped Django auth.

Never connects to a shared DB, uses existing cloud defaults, or qualifies the
Flind ingest SDK / Kafka / application release. All servers are process-owned.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

if __package__:
    from .qualify_django_lock import audit_runtime_lock
    from .qualify_ephemeral_postgres import isolated_postgres
    from .qualify_ephemeral_redis import isolated_redis
    from .qualify_ephemeral_clickhouse import isolated_clickhouse
    from .qualify_auth_session_wave59 import migrate_auth_and_sessions
    from .qualify_service_versions import source_requirements, version_matches_spec
else:
    from qualify_django_lock import audit_runtime_lock
    from qualify_ephemeral_postgres import isolated_postgres
    from qualify_ephemeral_redis import isolated_redis
    from qualify_ephemeral_clickhouse import isolated_clickhouse
    from qualify_auth_session_wave59 import migrate_auth_and_sessions
    from qualify_service_versions import source_requirements, version_matches_spec


def closed_receipt() -> dict:
    return {
        "exact_python_lock_passed": False,
        "postgres_17_isolated_passed": False,
        "framework_auth_session_schema_passed": False,
        "redis_isolated_passed": False,
        "clickhouse_isolated_passed": False,
        "clickhouse_http_sql_readback_passed": False,
        "redis_and_clickhouse_overlapped_postgres": False,
        "three_service_scoped_auth_qualified": False,
        "three_service_reachability_passed": False,
        "service_versions_qualified": False,
        "sdk_event_ingestion_qualified": False,
        "full_django_schema_qualified": False,
        "real_oauth_qualified": False,
        "tenant_isolation_qualified": False,
        "release_qualified": False,
    }


def selected_local_binary_is_valid(binary: str | None) -> bool:
    if binary is None:
        return True
    if not isinstance(binary, str) or not 1 <= len(binary) <= 4096:
        return False
    try:
        candidate = Path(binary)
        return candidate.is_absolute() and candidate.is_file() and os.access(candidate, os.X_OK)
    except OSError:
        return False


def private_service_probe(
    port: int, password: str, db_name: str,
    *, redis_binary: str | None = None,
    clickhouse_binary: str | None = None,
) -> dict:
    """Invoked only after the disposable PostgreSQL cluster is ready.

    PostgreSQL remains running while the other two nested service callbacks
    execute; auth migrations use the same ephemeral PostgreSQL database.
    No secret or raw service output is ever placed into the final receipt.
    """
    auth = migrate_auth_and_sessions(port, password, db_name)
    redis_args = {"binary": redis_binary} if redis_binary is not None else {}
    clickhouse_args = {"binary": clickhouse_binary} if clickhouse_binary is not None else {}
    redis = isolated_redis(
        on_ready=lambda redis_port: isolated_clickhouse(
            redis_port=redis_port, **clickhouse_args,
        ),
        **redis_args,
    )
    clickhouse = redis.get("nested_clickhouse") or {}
    ch_receipt = clickhouse.get("http_query_roundtrip") or {}
    service_rows = (clickhouse.get("service_versions") or {}).get("checks") or []
    observed_versions = {
        row.get("service"): row.get("version")
        for row in service_rows if isinstance(row, dict)
        and row.get("service") in ("redis", "clickhouse")
        and isinstance(row.get("version"), str)
        and len(row["version"]) <= 80
    }
    ch_roundtrip = (
        isinstance(ch_receipt, dict)
        and ch_receipt.get("rows") == 3
        and ch_receipt.get("sum") == 60
    )
    return {
        "framework_auth_session_schema_passed": bool(
            auth.get("django_framework_auth_session_qualified")
        ),
        "framework_scoped_migration_stages": [
            {
                "app": stage.get("app") if stage.get("app") in ("auth", "posthog_session") else None,
                "command_completed": bool(stage.get("command_completed")),
            }
            for stage in auth.get("stages", [])[:2]
        ],
        "redis_isolated_passed": bool(redis.get("isolated_redis_passed")),
        "clickhouse_isolated_passed": bool(clickhouse.get("isolated_clickhouse_passed")),
        "clickhouse_http_sql_readback_passed": bool(ch_roundtrip),
        "redis_and_clickhouse_overlapped_postgres": bool(
            redis.get("isolated_redis_passed")
            and clickhouse.get("isolated_clickhouse_passed")
            and ch_roundtrip
        ),
        "observed_service_versions": observed_versions,
    }


def qualify_private_triad(
    redis_binary: str | None = None,
    clickhouse_binary: str | None = None,
) -> dict:
    if not selected_local_binary_is_valid(redis_binary) or not selected_local_binary_is_valid(clickhouse_binary):
        return {**closed_receipt(), "blocker": "Selected local server binary is not executable"}
    try:
        locked = bool(audit_runtime_lock().get("direct_lock_qualified"))
    except (OSError, ValueError, KeyError):
        locked = False
    if not locked:
        return {
            **closed_receipt(),
            "blocker": "Exact Python dependency lock incomplete",
        }

    postgres = isolated_postgres(
        on_ready=lambda port, password, name: private_service_probe(
            port, password, name,
            redis_binary=redis_binary,
            clickhouse_binary=clickhouse_binary,
        )
    )
    scoped = postgres.get("django_migration_plan") or {}
    clean = closed_receipt()
    clean.update({
        "exact_python_lock_passed": True,
        "postgres_17_isolated_passed": bool(postgres.get("postgres_component_passed")),
        "framework_auth_session_schema_passed": bool(
            postgres.get("postgres_component_passed")
            and scoped.get("framework_auth_session_schema_passed")
        ),
        "redis_isolated_passed": bool(scoped.get("redis_isolated_passed")),
        "clickhouse_isolated_passed": bool(scoped.get("clickhouse_isolated_passed")),
        "clickhouse_http_sql_readback_passed": bool(
            scoped.get("clickhouse_http_sql_readback_passed")
        ),
        "redis_and_clickhouse_overlapped_postgres": bool(
            postgres.get("postgres_component_passed")
            and scoped.get("redis_and_clickhouse_overlapped_postgres")
        ),
    })
    clean["three_service_reachability_passed"] = all(
        clean[key] for key in (
            "exact_python_lock_passed",
            "postgres_17_isolated_passed",
            "framework_auth_session_schema_passed",
            "redis_isolated_passed",
            "clickhouse_isolated_passed",
            "clickhouse_http_sql_readback_passed",
            "redis_and_clickhouse_overlapped_postgres",
        )
    )
    # An SQL roundtrip does not make an unsupported Redis/ClickHouse safe.
    # The specs are read from the real Flind settings source, never invented
    # or silently upgraded to match whichever binaries happen to be present.
    observed = dict(scoped.get("observed_service_versions") or {})
    pg_version = postgres.get("postgres_version")
    if isinstance(pg_version, str) and len(pg_version) <= 80:
        observed["postgresql"] = pg_version
    try:
        specs = source_requirements()
        clean["service_versions_qualified"] = bool(all(
            isinstance(observed.get(service), str)
            and version_matches_spec(observed[service], specs[service])
            for service in ("postgresql", "redis", "clickhouse")
        ))
    except (OSError, ValueError, KeyError, TypeError, SyntaxError):
        clean["service_versions_qualified"] = False
    # Version strings are not credentials, and are safe for mismatch audits.
    clean["observed_service_versions"] = {
        service: observed.get(service)
        for service in ("postgresql", "redis", "clickhouse")
    }
    clean["three_service_scoped_auth_qualified"] = bool(
        clean["three_service_reachability_passed"]
        and clean["service_versions_qualified"]
    )
    clean["framework_scoped_migration_stages"] = scoped.get(
        "framework_scoped_migration_stages", []
    )
    if not clean["three_service_scoped_auth_qualified"]:
        clean["blocker"] = (
            "Local Redis/ClickHouse/PostgreSQL versions outside the Flind requirements"
            if clean["three_service_reachability_passed"]
            and not clean["service_versions_qualified"]
            else "At least one isolated component or auth/session migration failed"
        )
    return clean


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--redis-bin", help="Absolute path to compatible local redis-server executable")
    parser.add_argument("--clickhouse-bin", help="Absolute path to compatible local clickhouse executable")
    args = parser.parse_args(argv)
    report = qualify_private_triad(args.redis_bin, args.clickhouse_bin)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Isolated three-service and scoped auth receipt:", (
            "PASS" if report["three_service_scoped_auth_qualified"] else "BLOCKED"
        ))
        print("Full Flind app, SDK ingestion and release: NOT QUALIFIED")
    return 0 if report["three_service_scoped_auth_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
