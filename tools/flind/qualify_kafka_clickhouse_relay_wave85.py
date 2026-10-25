#!/usr/bin/env python3
"""Synthetic Kafka CLI -> Python relay -> real temporary ClickHouse probe.

This is deliberately NOT the Flind production ingestion consumer, SDK,
materialized-view pipeline, or dashboard E2E. Only fixed synthetic payloads
are accepted; no shared services, live tenant data or paid cloud.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from uuid import UUID

if __package__:
    from .qualify_ephemeral_kafka_wave84 import EVENTS, qualify_kafka
    from .qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http
    from .qualify_event_store_wave83 import original_event_columns_present
else:
    from qualify_ephemeral_kafka_wave84 import EVENTS, qualify_kafka
    from qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http
    from qualify_event_store_wave83 import original_event_columns_present

TABLE = "flind_wave85_relay_events"
CREATE_SQL = (
    f"CREATE TABLE {TABLE} "
    "(uuid UUID,event String,properties String,"
    "timestamp DateTime64(6,'UTC'),team_id Int64,distinct_id String) "
    "ENGINE=Memory"
)


def admitted_records(records: tuple[dict, ...]) -> bool:
    """Never replay untrusted Kafka messages or another project's records."""
    return (
        type(records) is tuple
        and len(records) == len(EVENTS)
        and all(type(record) is dict and record == expected
                for record, expected in zip(records, EVENTS))
    )


def insert_statement(index: int, records: tuple[dict, ...]) -> str:
    if not admitted_records(records) or type(index) is not int or not 0 <= index < len(EVENTS):
        raise ValueError("Only the exact fixed synthetic Kafka event fixture is allowed")
    record = records[index]
    team = record["team_id"]
    distinct = record["distinct_id"]
    event = record["event"]
    properties = json.dumps(record["properties"], ensure_ascii=True, separators=(",", ":"))
    uuid = UUID(int=index + 101)
    sql = (
        f"INSERT INTO {TABLE} (uuid,event,properties,timestamp,team_id,distinct_id) "
        f"VALUES ('{uuid}','{event}','{properties}',"
        f"'2026-10-25 00:00:00',{team},'{distinct}')"
    )
    if not sql.isascii() or len(sql) > 256:
        raise ValueError("Synthetic relay statement exceeds bounded ClickHouse client")
    return sql


def relay_readback(port: int, records: tuple[dict, ...]) -> dict:
    """Perform actual ClickHouse queries against replayed Kafka CLI records."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid private ClickHouse port")
    if not admitted_records(records) or not original_event_columns_present():
        raise ValueError("Only canonical, fixed synthetic Flind event fields accepted")
    sql_http(port, CREATE_SQL)
    try:
        for i in range(len(records)):
            sql_http(port, insert_statement(i, records))
        for team, expected in ((101, b"2\t1\t1\t1"), (202, b"1\t1\t1\t0")):
            query = (
                "SELECT count(),countIf(event='$pageview'),"
                "uniqExactIf(distinct_id,event='$pageview'),"
                "countIf(event='purchase') "
                f"FROM {TABLE} WHERE team_id={team}"
            )
            if sql_http(port, query).strip() != expected:
                raise ValueError("Team-scoped Kafka relay aggregate mismatch")
        for team, path in ((101, "/private"), (202, "/home")):
            query = f"SELECT count() FROM {TABLE} WHERE team_id={team} AND properties LIKE '%{path}%'"
            if sql_http(port, query).strip() != b"0":
                raise ValueError("Kafka relay cross-team scoped-query isolation failed")
        return {
            "synthetic_relay_passed": True,
            "real_clickhouse_relay_readback": True,
            "kafka_records_replayed": len(records),
            "team_101": {"rows": 2, "pageviews": 1, "unique_ids": 1, "purchases": 1},
            "team_202": {"rows": 1, "pageviews": 1, "unique_ids": 1, "purchases": 0},
            "cross_team_path_reads_absent": True,
            "temporary_memory_table": True,
        }
    finally:
        sql_http(port, f"DROP TABLE IF EXISTS {TABLE}")


def _clickhouse_from_consumed(records: tuple[dict, ...]) -> dict:
    if not admitted_records(records):
        raise ValueError("Kafka consumer returned unexpected synthetic events")
    cluster = isolated_clickhouse(on_ready=lambda port: relay_readback(port, records))
    receipt = cluster.get("event_readback") or {}
    ok = (cluster.get("isolated_clickhouse_passed") is True
          and receipt.get("synthetic_relay_passed") is True
          and receipt.get("cross_team_path_reads_absent") is True)
    return {
        "synthetic_relay_passed": ok,
        "private_clickhouse_passed": cluster.get("isolated_clickhouse_passed") is True,
        "kafka_records_replayed": receipt.get("kafka_records_replayed", 0) if ok else 0,
        "cross_team_path_reads_absent": ok,
    }


def qualify_joint_relay(kafka_home: Path) -> dict:
    kafka = qualify_kafka(kafka_home, on_consumed=_clickhouse_from_consumed)
    receipt = kafka.get("synthetic_relay") or {}
    ok = (
        kafka.get("isolated_kafka_passed") is True
        and kafka.get("exact_json_message_roundtrip") is True
        and receipt.get("synthetic_relay_passed") is True
        and receipt.get("private_clickhouse_passed") is True
        and receipt.get("kafka_records_replayed") == len(EVENTS)
    )
    return {
        "synthetic_kafka_cli_to_clickhouse_relay_qualified": ok,
        "actual_kafka_transport_passed": kafka.get("isolated_kafka_passed") is True,
        "actual_clickhouse_replay_passed": ok,
        "synthetic_messages_replayed": len(EVENTS) if ok else 0,
        "private_temporary_services_only": True,
        "sdk_ingestion_qualified": False,
        "flind_production_ingester_qualified": False,
        "production_kafka_to_clickhouse_qualified": False,
        "production_events_schema_qualified": False,
        "dashboard_query_qualified": False,
        "tenant_authorization_qualified": False,
        "release_qualified": False,
        **({"blocker": kafka.get("blocker") or "Synthetic private relay did not qualify"} if not ok else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kafka-home", required=True, type=Path,
                        help="Absolute path to local verified Apache Kafka 4.3.1 distribution")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_joint_relay(args.kafka_home)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Synthetic local Kafka CLI -> ClickHouse relay:",
              "PASS" if result["synthetic_kafka_cli_to_clickhouse_relay_qualified"] else "BLOCKED")
        print("Flind production capture/ingestion/dashboard: NOT QUALIFIED")
    return 0 if result["synthetic_kafka_cli_to_clickhouse_relay_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
