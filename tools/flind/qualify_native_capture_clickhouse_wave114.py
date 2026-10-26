#!/usr/bin/env python3
"""Native Rust Capture -> real Kafka -> ClickHouse Kafka-engine materialized view.

PROOF SCOPE: real compiled Rust HTTP->Kafka producer and a real ClickHouse Kafka
ENGINE subscriber storing synthetic events in an isolated Memory table. The
production Node.js ingestion worker / product events schema are NOT involved.
"""
from __future__ import annotations

import argparse
from http.client import HTTPConnection
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from tools.flind.qualify_ephemeral_kafka_wave84 import qualify_kafka
from tools.flind.qualify_ephemeral_clickhouse import isolated_clickhouse
from tools.flind.qualify_native_capture_kafka_wave113 import (
    CAPTURE, REDIS, DEFAULT_HOME, real_native_roundtrip,
)

CLICKHOUSE = Path("/tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64")
TOPIC = "flind-wave113-native-analytics"
TABLE = "flind_wave114_native_events"
SOURCE = "flind_wave114_kafka_source"
VIEW = "flind_wave114_kafka_to_memory"


def sql(port: int, query: str) -> str:
    """Do not redirect, ever. Bound SQL and response byte lengths."""
    if not isinstance(port, int) or not 1024 <= port <= 65535 or len(query) > 1500 or not query.isascii():
        raise ValueError("Unsafe ClickHouse test request")
    conn = HTTPConnection("127.0.0.1", port, timeout=4)
    try:
        conn.request("POST", "/", body=query.encode("ascii"),
                     headers={"Content-Type": "text/plain"})
        response = conn.getresponse()
        raw = response.read(8192)
        if response.status != 200 or len(raw) > 8000:
            raise ValueError(f"ClickHouse isolated SQL refused ({response.status}): {raw[:350]!r}")
        return raw.decode("utf-8").strip()
    finally:
        conn.close()


def read_native_kafka_via_clickhouse(port: int, bootstrap: str, record: dict) -> dict:
    result = {
        "real_clickhouse_kafka_engine_subscription": False,
        "native_rust_record_in_memory_table": False,
        "uuid_matches_native_capture_kafka": False,
        "separate_synthetic_token_filter": False,
        "only_one_native_event": False,
        "production_ingestion_worker_executed": False,
        "production_events_table_qualified": False,
        "authenticated_product_api_qualified": False,
        "release_qualified": False,
    }
    if (
        not re.fullmatch(r"127\.0\.0\.1:\d{4,5}", bootstrap)
        or not isinstance(record, dict)
        or not re.fullmatch(r"[0-9a-f-]{36}", str(record.get("uuid", "")))
        or record.get("event") != "$pageview"
        or record.get("distinct_id") != "flind-wave112-synthetic"
        or record.get("token") != "flind_synthetic_internal_token"
    ):
        raise ValueError("Only the exact Rust-observed private synthetic Kafka record may be consumed")
    if sql(port, "SELECT name FROM system.table_engines WHERE name='Kafka'") != "Kafka":
        raise ValueError("Supported ClickHouse Kafka engine unavailable")
    result["real_clickhouse_kafka_engine_subscription"] = True
    # No manual INSERT: ClickHouse's own Kafka engine subscribes to the topic
    # produced by native Rust Capture, and a materialized view selects columns
    # into the Memory table. No production product-events table is touched.
    sql(port, f"CREATE TABLE {TABLE} (uuid String,event String,distinct_id String,token String) ENGINE=Memory")
    try:
        sql(port, (
            f"CREATE TABLE {SOURCE} (uuid String,event String,distinct_id String,token String) "
            f"ENGINE=Kafka SETTINGS kafka_broker_list='{bootstrap}',"
            f"kafka_topic_list='{TOPIC}',kafka_group_name='flind_wave114_native_probe',"
            "kafka_format='JSONEachRow',kafka_num_consumers=1"
        ))
        try:
            sql(port, (
                f"CREATE MATERIALIZED VIEW {VIEW} TO {TABLE} AS "
                f"SELECT uuid,event,distinct_id,token FROM {SOURCE}"
            ))
            try:
                expected = record["uuid"]
                end = time.monotonic() + 24
                observed = []
                while time.monotonic() < end:
                    raw = sql(port, (
                        f"SELECT uuid,event,distinct_id,token FROM {TABLE} FORMAT JSONEachRow"
                    ))
                    observed = [json.loads(line) for line in raw.splitlines() if line.strip()]
                    if len(observed) >= 1:
                        break
                    time.sleep(0.4)
                result["only_one_native_event"] = len(observed) == 1
                result["uuid_matches_native_capture_kafka"] = (
                    len(observed) == 1 and observed[0].get("uuid") == expected
                )
                result["native_rust_record_in_memory_table"] = (
                    result["uuid_matches_native_capture_kafka"]
                    and observed[0].get("event") == "$pageview"
                    and observed[0].get("distinct_id") == "flind-wave112-synthetic"
                    and observed[0].get("token") == "flind_synthetic_internal_token"
                )
                total_for_unknown = sql(port, (
                    f"SELECT count() FROM {TABLE} WHERE token='synthetic_not_this_token'"
                ))
                result["separate_synthetic_token_filter"] = total_for_unknown == "0"
                result["real_clickhouse_kafka_engine_subscription"] &= (
                    result["native_rust_record_in_memory_table"]
                    and result["only_one_native_event"]
                    and result["separate_synthetic_token_filter"]
                )
                return result
            finally:
                sql(port, f"DROP VIEW IF EXISTS {VIEW}")
        finally:
            sql(port, f"DROP TABLE IF EXISTS {SOURCE}")
    finally:
        sql(port, f"DROP TABLE IF EXISTS {TABLE}")


def native_record_to_clickhouse(bootstrap: str, record: dict) -> dict:
    if not CLICKHOUSE.is_file() or shutil.disk_usage("/tmp").free < 10 * 1024**3:
        return {"real_clickhouse_kafka_engine_subscription": False,
                "blocker": "Supported ClickHouse binary or 10GiB disk reserve missing"}
    service = isolated_clickhouse(
        binary=str(CLICKHOUSE),
        on_ready=lambda port: read_native_kafka_via_clickhouse(port, bootstrap, record),
    )
    output = service.get("event_readback") or {}
    passed = (
        service.get("isolated_clickhouse_passed") is True
        and output.get("real_clickhouse_kafka_engine_subscription") is True
        and output.get("native_rust_record_in_memory_table") is True
        and output.get("only_one_native_event") is True
    )
    return {
        "native_kafka_to_real_clickhouse_memory": passed,
        "clickhouse_engine_receipt": output,
        "production_ingester_qualified": False,
        "production_events_table_qualified": False,
        "tenant_auth_api_qualified": False,
        "dashboard_browser_e2e": False,
        "release_qualified": False,
        **({"blocker": str(service.get("reason", "Native Kafka to ClickHouse readback failed"))[:450]}
           if not passed else {}),
    }


def qualify(kafka_home: Path = DEFAULT_HOME) -> dict:
    report = {
        "actual_native_rust_to_kafka_to_clickhouse": False,
        "kafka_431_real_broker": False,
        "native_capture_delivered_exact_uuid": False,
        "clickhouse_kafka_materialized_memory_event": False,
        "production_node_ingester_qualified": False,
        "production_events_table_qualified": False,
        "authenticated_tenant_query_qualified": False,
        "dashboard_e2e_qualified": False,
        "release_qualified": False,
    }
    if (not CAPTURE.is_file() or not REDIS.is_file() or not CLICKHOUSE.is_file()
            or shutil.disk_usage("/tmp").free < 10 * 1024**3):
        return {**report, "blocker": "Native binaries or 10GiB disk reserve missing"}
    try:
        broker = qualify_kafka(
            kafka_home,
            on_broker_ready=lambda bootstrap: real_native_roundtrip(
                bootstrap, kafka_home,
                on_native_consumed=native_record_to_clickhouse,
            ),
        )
        native = broker.get("native_capture_relay") or {}
        downstream = native.get("native_downstream_probe") or {}
        ok = (
            broker.get("isolated_kafka_passed") is True
            and native.get("actual_native_capture_kafka_roundtrip") is True
            and downstream.get("native_kafka_to_real_clickhouse_memory") is True
            and native.get("owned_capture_stopped") is True
            and native.get("owned_redis_stopped") is True
        )
        report.update({
            "actual_native_rust_to_kafka_to_clickhouse": ok,
            "kafka_431_real_broker": broker.get("isolated_kafka_passed") is True,
            "native_capture_delivered_exact_uuid": native.get("actual_native_capture_kafka_roundtrip") is True,
            "clickhouse_kafka_materialized_memory_event":
                downstream.get("native_kafka_to_real_clickhouse_memory") is True,
            "clickhouse_receipt": downstream,
            **({"blocker": broker.get("blocker") or
                downstream.get("blocker") or native.get("blocker") or "Three-service pipeline not qualified"}
               if not ok else {}),
        })
        return report
    except (OSError, ValueError, subprocess.SubprocessError):
        return {**report, "blocker": "Native Rust Kafka ClickHouse rig failed"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kafka-home", type=Path, default=DEFAULT_HOME)
    a = p.parse_args()
    receipt = qualify(a.kafka_home)
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["actual_native_rust_to_kafka_to_clickhouse"] else 2)
