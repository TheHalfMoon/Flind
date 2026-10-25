#!/usr/bin/env python3
"""Four native, compatible loopback services with exact synthetic Kafka event SQL relay.

This harness is not Flind's SDK, Capture Rust server, native Kafka ingester,
authenticated query API or dashboard. It never promotes those release gates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .qualify_django_lock import audit_runtime_lock
    from .qualify_ephemeral_postgres import isolated_postgres
    from .qualify_ephemeral_redis import isolated_redis
    from .qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http
    from .qualify_ephemeral_kafka_wave84 import EVENTS, qualify_kafka, kafka_paths
    from .qualify_kafka_clickhouse_relay_wave85 import admitted_records, relay_readback
    from .qualify_auth_session_wave59 import migrate_auth_and_sessions
    from .qualify_local_binaries_wave74 import qualify_binary_versions
    from .qualify_service_versions import source_requirements, version_matches_spec
else:
    from qualify_django_lock import audit_runtime_lock
    from qualify_ephemeral_postgres import isolated_postgres
    from qualify_ephemeral_redis import isolated_redis
    from qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http
    from qualify_ephemeral_kafka_wave84 import EVENTS, qualify_kafka, kafka_paths
    from qualify_kafka_clickhouse_relay_wave85 import admitted_records, relay_readback
    from qualify_auth_session_wave59 import migrate_auth_and_sessions
    from qualify_local_binaries_wave74 import qualify_binary_versions
    from qualify_service_versions import source_requirements, version_matches_spec


def empty(blocker: str = "Four-service synthetic qualification incomplete") -> dict:
    return {
        "four_native_services_synthetic_qualified": False,
        "exact_python_lock_passed": False,
        "kafka_431_transport_passed": False,
        "postgres_scoped_django_auth_passed": False,
        "redis_7_private_store_passed": False,
        "clickhouse_supported_sql_passed": False,
        "three_exact_events_replayed": False,
        "cross_team_sql_filters_passed": False,
        "all_service_versions_supported": False,
        "process_owned_temporary_services": True,
        "production_capture_rust_qualified": False,
        "production_sdk_http_qualified": False,
        "production_kafka_ingester_qualified": False,
        "production_events_schema_qualified": False,
        "production_query_api_qualified": False,
        "production_tenant_authorization_qualified": False,
        "dashboard_e2e_qualified": False,
        "release_qualified": False,
        "blocker": blocker,
    }


def qualify_four_services(kafka_home: Path, redis_binary: str, clickhouse_binary: str) -> dict:
    receipt = empty()
    try:
        requirements = source_requirements()
        if not audit_runtime_lock()["direct_lock_qualified"]:
            return {**receipt, "blocker": "Exact Django Python dependencies not locked"}
        receipt["exact_python_lock_passed"] = True
        binaries = qualify_binary_versions(redis_binary, clickhouse_binary)
        if not binaries["service_binary_versions_qualified"]:
            return {**receipt, "blocker": "Redis/ClickHouse executable version not supported"}
        kafka_paths(kafka_home)
    except (OSError, ValueError, SyntaxError, TypeError, KeyError):
        return {**receipt, "blocker": "Local executable or source compatibility unavailable"}

    def _on_consumed(records: tuple[dict, ...]) -> dict:
        if not admitted_records(records):
            raise ValueError("Kafka returned nonfixture messages")

        def _on_postgres(pg_port: int, password: str, db_name: str) -> dict:
            auth = migrate_auth_and_sessions(pg_port, password, db_name)
            if auth.get("django_framework_auth_session_qualified") is not True:
                return {"scoped_auth": False}

            def _on_redis(redis_port: int) -> dict:
                def _on_clickhouse(ch_port: int) -> dict:
                    observed = sql_http(ch_port, "SELECT version()").decode("ascii").strip()
                    if not version_matches_spec(observed, requirements["clickhouse"]):
                        raise ValueError("Running ClickHouse server not supported")
                    return relay_readback(ch_port, records)

                return isolated_clickhouse(
                    binary=clickhouse_binary, redis_port=redis_port,
                    on_ready=_on_clickhouse,
                )

            redis = isolated_redis(binary=redis_binary, on_ready=_on_redis)
            clickhouse = redis.get("nested_clickhouse") or {}
            events = clickhouse.get("event_readback") or {}
            checks = (clickhouse.get("service_versions") or {}).get("checks") or []
            versions = {
                item.get("service"): item.get("version")
                for item in checks if isinstance(item, dict)
                and item.get("service") in ("redis", "clickhouse")
            }
            compatible = all(
                isinstance(versions.get(name), str)
                and version_matches_spec(versions[name], requirements[name])
                for name in ("redis", "clickhouse")
            )
            ok = (
                redis.get("isolated_redis_passed") is True
                and clickhouse.get("isolated_clickhouse_passed") is True
                and events.get("synthetic_relay_passed") is True
                and events.get("cross_team_path_reads_absent") is True
                and events.get("kafka_records_replayed") == len(EVENTS)
                and compatible
                and (clickhouse.get("http_query_roundtrip") or {}).get("rows") == 3
            )
            return {
                "scoped_auth": True,
                "redis": redis.get("isolated_redis_passed") is True,
                "clickhouse": clickhouse.get("isolated_clickhouse_passed") is True,
                "three_events": events.get("kafka_records_replayed") == len(EVENTS),
                "team_sql_isolation": events.get("cross_team_path_reads_absent") is True,
                "nested_runtime_versions": compatible,
                "joined": ok,
            }

        pg = isolated_postgres(on_ready=_on_postgres)
        joined = pg.get("django_migration_plan") or {}
        version = pg.get("postgres_version")
        pg_ok = (
            pg.get("postgres_component_passed") is True
            and isinstance(version, str)
            and version_matches_spec(version, requirements["postgresql"])
        )
        ok = pg_ok and joined.get("joined") is True
        return {
            "postgres_auth": bool(pg_ok and joined.get("scoped_auth") is True),
            "redis": bool(ok and joined.get("redis") is True),
            "clickhouse": bool(ok and joined.get("clickhouse") is True),
            "three_events": bool(ok and joined.get("three_events") is True),
            "team_sql_isolation": bool(ok and joined.get("team_sql_isolation") is True),
            "versions": bool(ok and joined.get("nested_runtime_versions") is True),
            "four_service_joined": bool(ok),
        }

    kafka = qualify_kafka(kafka_home, on_consumed=_on_consumed)
    child = kafka.get("synthetic_relay") or {}
    actual_kafka = (
        kafka.get("isolated_kafka_passed") is True
        and kafka.get("exact_json_message_roundtrip") is True
        and kafka.get("synthetic_events_consumed") == len(EVENTS)
    )
    receipt.update({
        "kafka_431_transport_passed": actual_kafka,
        "postgres_scoped_django_auth_passed": child.get("postgres_auth") is True,
        "redis_7_private_store_passed": child.get("redis") is True,
        "clickhouse_supported_sql_passed": child.get("clickhouse") is True,
        "three_exact_events_replayed": child.get("three_events") is True,
        "cross_team_sql_filters_passed": child.get("team_sql_isolation") is True,
        "all_service_versions_supported": child.get("versions") is True,
    })
    complete = actual_kafka and child.get("four_service_joined") is True and all(
        receipt[key] for key in (
            "postgres_scoped_django_auth_passed", "redis_7_private_store_passed",
            "clickhouse_supported_sql_passed", "three_exact_events_replayed",
            "cross_team_sql_filters_passed", "all_service_versions_supported",
        )
    )
    receipt["four_native_services_synthetic_qualified"] = bool(complete)
    if complete:
        receipt.pop("blocker")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kafka-home", type=Path, required=True)
    parser.add_argument("--redis-bin", required=True)
    parser.add_argument("--clickhouse-bin", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_four_services(args.kafka_home, args.redis_bin, args.clickhouse_bin)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Four native synthetic services:", "PASS" if result["four_native_services_synthetic_qualified"] else "BLOCKED")
        print("Production SDK, native capture and release: NOT QUALIFIED")
    return 0 if result["four_native_services_synthetic_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
