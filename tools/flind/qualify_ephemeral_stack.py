#!/usr/bin/env python3
"""Test simultaneous temporary Redis+ClickHouse+Python+Django+PostgreSQL readiness.

This is NOT an application startup, production readiness or SDK/Django E2E.
Both temporary servers are process-scoped, local-only and automatically stopped.
"""
from __future__ import annotations

import argparse
import json
import sys

if __package__:
    from .qualify_ephemeral_redis import isolated_redis
    from .qualify_ephemeral_clickhouse import isolated_clickhouse
else:
    from qualify_ephemeral_redis import isolated_redis
    from qualify_ephemeral_clickhouse import isolated_clickhouse


def qualify_stack(
    redis_binary: str | None = None,
    clickhouse_binary: str | None = None,
) -> dict:
    redis_result = isolated_redis(
        binary=redis_binary,
        on_ready=lambda redis_port: isolated_clickhouse(
            binary=clickhouse_binary, redis_port=redis_port,
        ),
    )
    clickhouse = redis_result.get("nested_clickhouse", {})
    prerequisites = clickhouse.get("backend_prerequisites", {})
    service_versions = clickhouse.get("service_versions", {})
    success = bool(
        redis_result.get("isolated_redis_passed")
        and clickhouse.get("isolated_clickhouse_passed")
        and prerequisites.get("prerequisites_ready")
    )
    return {
        "stack_prerequisites_passed": success,
        "service_versions_supported": bool(service_versions.get("version_requirements_met")),
        "app_runtime_compatible": bool(
            success and service_versions.get("version_requirements_met")
        ),
        "release_qualified": False,
        "redis_real_roundtrip": bool(redis_result.get("isolated_redis_passed")),
        "clickhouse_http_sql_roundtrip": clickhouse.get("http_query_roundtrip"),
        "backend_prerequisites": prerequisites,
        "service_versions": service_versions,
        "service_failure_reason": clickhouse.get("reason"),
        "qualification_note": (
            "Only temporary service primitives and Python/Django availability "
            "were checked; no Flind app startup, migrations, SDK capture, "
            "ClickHouse event pipeline, auth or tenant E2E occurred"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--redis-bin", help="Isolated Redis binary path")
    parser.add_argument("--clickhouse-bin", help="Isolated ClickHouse binary path")
    args = parser.parse_args(argv)
    result = qualify_stack(args.redis_bin, args.clickhouse_bin)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind temporary stack prerequisites: " +
              ("PASS" if result["stack_prerequisites_passed"] else "BLOCKED"))
        print("Flind service versions: " +
              ("SUPPORTED" if result["service_versions_supported"] else "UNSUPPORTED"))
        print("Flind release E2E: NOT QUALIFIED")
    return 0 if result["app_runtime_compatible"] else 2


if __name__ == "__main__":
    sys.exit(main())
