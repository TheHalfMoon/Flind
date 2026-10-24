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


def qualify_stack() -> dict:
    redis_result = isolated_redis(
        on_ready=lambda redis_port: isolated_clickhouse(redis_port=redis_port),
    )
    clickhouse = redis_result.get("nested_clickhouse", {})
    prerequisites = clickhouse.get("backend_prerequisites", {})
    success = bool(
        redis_result.get("isolated_redis_passed")
        and clickhouse.get("isolated_clickhouse_passed")
        and prerequisites.get("prerequisites_ready")
    )
    return {
        "stack_prerequisites_passed": success,
        "release_qualified": False,
        "redis_real_roundtrip": bool(redis_result.get("isolated_redis_passed")),
        "clickhouse_http_sql_roundtrip": clickhouse.get("http_query_roundtrip"),
        "backend_prerequisites": prerequisites,
        "qualification_note": (
            "Only temporary service primitives and Python/Django availability "
            "were checked; no Flind app startup, migrations, SDK capture, "
            "ClickHouse event pipeline, auth or tenant E2E occurred"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_stack()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind temporary stack prerequisites: " +
              ("PASS" if result["stack_prerequisites_passed"] else "BLOCKED"))
        print("Flind release E2E: NOT QUALIFIED")
    return 0 if result["stack_prerequisites_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
