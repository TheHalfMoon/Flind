#!/usr/bin/env python3
"""Qualify a version-compatible real Kafka -> temporary ClickHouse synthetic relay.

Never treats synthetic transport or temporary Memory-table reads as production
SDK ingestion, tenant authorization, dashboard E2E or release eligibility.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .qualify_ephemeral_kafka_wave84 import EVENTS, qualify_kafka
    from .qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http
    from .qualify_kafka_clickhouse_relay_wave85 import admitted_records, relay_readback
    from .qualify_local_binaries_wave74 import inspect_binary
    from .qualify_service_versions import source_requirements, version_matches_spec
else:
    from qualify_ephemeral_kafka_wave84 import EVENTS, qualify_kafka
    from qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http
    from qualify_kafka_clickhouse_relay_wave85 import admitted_records, relay_readback
    from qualify_local_binaries_wave74 import inspect_binary
    from qualify_service_versions import source_requirements, version_matches_spec


def _not_qualified(blocker: str) -> dict:
    return {
        "supported_kafka_clickhouse_synthetic_relay_qualified": False,
        "native_kafka_transport_passed": False,
        "supported_clickhouse_runtime_passed": False,
        "exact_synthetic_event_readback_passed": False,
        "production_sdk_ingestion_qualified": False,
        "production_kafka_consumer_qualified": False,
        "production_clickhouse_schema_qualified": False,
        "dashboard_query_qualified": False,
        "tenant_authorization_qualified": False,
        "release_qualified": False,
        "blocker": blocker,
    }


def qualify_supported_relay(kafka_home: Path, clickhouse_binary: str) -> dict:
    """Require both executable-version admission and observed server compatibility.

    A failing preflight does not launch either Kafka or ClickHouse.
    A running ClickHouse server's actual version must also pass source specs.
    """
    try:
        spec = source_requirements()["clickhouse"]
        inspected = inspect_binary("clickhouse", clickhouse_binary, spec)
    except (OSError, ValueError, SyntaxError, TypeError, KeyError):
        return _not_qualified("ClickHouse source version requirements unavailable")
    if not inspected["supported_version"]:
        return _not_qualified("Selected local ClickHouse binary unsupported or unavailable")

    def _on_consumed(records: tuple[dict, ...]) -> dict:
        if not admitted_records(records):
            raise ValueError("Kafka delivered non-fixture events")

        def _on_clickhouse_ready(port: int) -> dict:
            # Do not trust --version alone; query this actual loopback server.
            observed = sql_http(port, "SELECT version()").decode("ascii").strip()
            if not version_matches_spec(observed, spec):
                raise ValueError("Running ClickHouse version is unsupported")
            return {**relay_readback(port, records), "running_version_supported": True}

        service = isolated_clickhouse(binary=clickhouse_binary, on_ready=_on_clickhouse_ready)
        replay = service.get("event_readback") or {}
        ok = (
            service.get("isolated_clickhouse_passed") is True
            and replay.get("running_version_supported") is True
            and replay.get("synthetic_relay_passed") is True
            and replay.get("cross_team_path_reads_absent") is True
            and replay.get("kafka_records_replayed") == len(EVENTS)
        )
        return {
            "supported_clickhouse_relay_passed": ok,
            "running_version_supported": replay.get("running_version_supported") is True,
            "readback_rows": len(EVENTS) if ok else 0,
        }

    kafka = qualify_kafka(kafka_home, on_consumed=_on_consumed)
    relay = kafka.get("synthetic_relay") or {}
    kafka_ok = (
        kafka.get("isolated_kafka_passed") is True
        and kafka.get("exact_json_message_roundtrip") is True
        and kafka.get("synthetic_events_consumed") == len(EVENTS)
    )
    clickhouse_ok = (
        relay.get("supported_clickhouse_relay_passed") is True
        and relay.get("running_version_supported") is True
        and relay.get("readback_rows") == len(EVENTS)
    )
    result = _not_qualified("Supported native synthetic relay unavailable")
    result.update({
        "supported_kafka_clickhouse_synthetic_relay_qualified": bool(kafka_ok and clickhouse_ok),
        "native_kafka_transport_passed": kafka_ok,
        "supported_clickhouse_runtime_passed": clickhouse_ok,
        "exact_synthetic_event_readback_passed": clickhouse_ok,
        "synthetic_event_count": len(EVENTS) if kafka_ok and clickhouse_ok else 0,
        "selected_clickhouse_version": inspected["observed_version"],
    })
    if kafka_ok and clickhouse_ok:
        result.pop("blocker")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kafka-home", required=True, type=Path)
    parser.add_argument("--clickhouse-bin", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_supported_relay(args.kafka_home, args.clickhouse_bin)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Compatible synthetic Kafka -> ClickHouse:",
              "PASS" if result["supported_kafka_clickhouse_synthetic_relay_qualified"] else "BLOCKED")
        print("Flind production pipeline/release: NOT QUALIFIED")
    return 0 if result["supported_kafka_clickhouse_synthetic_relay_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
