#!/usr/bin/env python3
"""Qualify three *disposable native prerequisites*, not the Flind application.

Use supported already-installed Redis and ClickHouse binaries. PostgreSQL 17 is
provisioned from the first-party isolated test harness. All three processes
overlap only on process-owned, nondefault loopback sockets, and are disposed of
by their existing try/finally cleanup. Never touches shared Redis/PG/CH.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil

from tools.flind.qualify_django_lock import audit_runtime_lock
from tools.flind.qualify_ephemeral_postgres import isolated_postgres
from tools.flind.qualify_ephemeral_redis import isolated_redis
from tools.flind.qualify_ephemeral_clickhouse import isolated_clickhouse
from tools.flind.qualify_service_versions import source_requirements, version_matches_spec

MIN_FREE_BYTES = 13 * (1024 ** 3)


def executable(path: str) -> bool:
    candidate = Path(path)
    return candidate.is_absolute() and candidate.is_file() and os.access(candidate, os.X_OK)


def qualify(redis_bin: str, clickhouse_bin: str) -> dict:
    receipt: dict = {
        "scope": "isolated native PostgreSQL/Redis/ClickHouse prerequisites only",
        "postgres_scoped": False,
        "redis_scoped": False,
        "clickhouse_scoped": False,
        "postgres_transaction_rolled_back": False,
        "all_source_versions_supported": False,
        "django_migrations_qualified": False,
        "real_sdk_ingestion_qualified": False,
        "real_worker_qualified": False,
        "query_api_qualified": False,
        "tenant_auth_qualified": False,
        "release_qualified": False,
        "three_native_prerequisites_qualified": False,
    }
    if not executable(redis_bin) or not executable(clickhouse_bin):
        return {**receipt, "blocker": "Required local compatible executable missing"}
    if shutil.disk_usage("/tmp").free < MIN_FREE_BYTES:
        return {**receipt, "blocker": "Refused: under 13 GiB free disk"}

    try:
        requirements = source_requirements()
    except (OSError, KeyError, TypeError, ValueError, SyntaxError):
        return {**receipt, "blocker": "Source service requirements could not be verified"}

    def on_postgres(port: int, _password: str, _db_name: str) -> dict:
        if port == 5432:
            raise ValueError("Non-disposable PostgreSQL port")
        def on_redis(redis_port: int) -> dict:
            if redis_port == 6379:
                raise ValueError("Non-disposable Redis port")
            return isolated_clickhouse(
                binary=clickhouse_bin, redis_port=redis_port,
            )

        redis = isolated_redis(binary=redis_bin, on_ready=on_redis)
        clickhouse = redis.get("nested_clickhouse") or {}
        sql = clickhouse.get("http_query_roundtrip") or {}
        checks = (clickhouse.get("service_versions") or {}).get("checks") or []
        versions = {
            item.get("service"): item.get("version")
            for item in checks if isinstance(item, dict)
            and item.get("service") in ("redis", "clickhouse")
        }
        return {
            "redis_scoped": redis.get("isolated_redis_passed") is True,
            "clickhouse_scoped": clickhouse.get("isolated_clickhouse_passed") is True,
            "redis_supported": bool(
                isinstance(versions.get("redis"), str)
                and version_matches_spec(versions["redis"], requirements["redis"])
            ),
            "clickhouse_supported": bool(
                isinstance(versions.get("clickhouse"), str)
                and version_matches_spec(versions["clickhouse"], requirements["clickhouse"])
            ),
            "clickhouse_rows": sql.get("rows"),
            "clickhouse_sum": sql.get("sum"),
            "isolated_network": redis.get("network") == "127.0.0.1 only"
            and clickhouse.get("network") == "127.0.0.1 only",
        }

    try:
        postgres = isolated_postgres(on_ready=on_postgres)
        nested = postgres.get("django_migration_plan") or {}
        receipt.update({
            "postgres_scoped": postgres.get("postgres_component_passed") is True,
            "postgres_transaction_rolled_back": postgres.get("transaction_rolled_back") is True,
            "redis_scoped": nested.get("redis_scoped") is True,
            "clickhouse_scoped": nested.get("clickhouse_scoped") is True,
            "postgres_rows": postgres.get("sql_rows"),
            "postgres_sum": postgres.get("sql_sum"),
            "clickhouse_rows": nested.get("clickhouse_rows"),
            "clickhouse_sum": nested.get("clickhouse_sum"),
            "all_source_versions_supported": bool(
                postgres.get("postgres_version")
                and version_matches_spec(postgres["postgres_version"], requirements["postgresql"])
                and nested.get("redis_supported")
                and nested.get("clickhouse_supported")
            ),
        })
        passed = all(receipt[k] for k in (
            "postgres_scoped", "postgres_transaction_rolled_back",
            "redis_scoped", "clickhouse_scoped", "all_source_versions_supported",
        )) and bool(
            nested.get("isolated_network") and receipt["postgres_rows"] == 3
            and receipt["postgres_sum"] == 14
            and receipt["clickhouse_rows"] == 3 and receipt["clickhouse_sum"] == 60
        )
        receipt["three_native_prerequisites_qualified"] = bool(passed)
        if not passed:
            receipt["blocker"] = "Native three-service receipt incomplete"
    except (OSError, RuntimeError, ValueError, TypeError, KeyError):
        receipt["blocker"] = "Could not qualify isolated native prerequisite services"

    lock = audit_runtime_lock()
    receipt["django_dependency_lock_qualified"] = lock["direct_lock_qualified"]
    receipt["django_missing_direct_dependencies"] = lock["missing_count"]
    receipt["django_mismatched_direct_dependencies"] = lock["version_mismatch_count"]
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--redis-bin", required=True)
    parser.add_argument("--clickhouse-bin", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = qualify(args.redis_bin, args.clickhouse_bin)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Native prerequisite overlap:",
              "PASS" if result["three_native_prerequisites_qualified"] else "BLOCKED")
        print("Flind application/Django/SDK release: NOT QUALIFIED")
    return 0 if result["three_native_prerequisites_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
