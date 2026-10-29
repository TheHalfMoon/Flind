#!/usr/bin/env python3
"""REAL owner-only Kafka ENGINE -> materialized view -> ClickHouse MergeTree probe.

Copy-first adaptation of Flind Waves 84, 114, 181 and 188. It uses the
original real private Kafka KRaft qualifier and original isolated ClickHouse
server, but deliberately uses a synthetic direct Kafka Producer: NOT Flind's
Rust/Node production ingest, authenticated tenant API, migrations or release.

Requires a source-pinned, owner-marked, official ClickHouse 25.12 macOS asset.
No existing Kafka/ClickHouse service, system config, user DB or customer data
is ever accessed. Fails closed if the Mac disk reserve cannot be maintained.
"""
from __future__ import annotations

import argparse
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from tools.flind import qualify_ephemeral_clickhouse as ch
from tools.flind.qualify_ephemeral_kafka_wave84 import EVENTS, qualify_kafka
from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import EXPECTED_COLUMNS, verified_schema
from tools.flind.qualify_supported_clickhouse_kafka_wave181 import source_clickhouse_spec, version_qualified
from tools.flind.qualify_supported_mergetree_durable_wave188 import (
    EXPECTED_VERSION, OFFICIAL_MAC_ARM64_SHA256,
)

ROOT = Path("/private/tmp")
ASSET_OWNER = "FLIND_WAVE253_CLICKHOUSE_2512_OWNER_ONLY_V1\n"
ASSET_SIZE = 123_762_120
FREE_START_BYTES = int(16.8 * 1024 ** 3)
FREE_BOOT_BYTES = int(16.45 * 1024 ** 3)
FREE_FLOOR_BYTES = int(15.5 * 1024 ** 3)
TOPIC = "flind-wave255-synthetic-kafka-engine"
SOURCE = "flind_wave255_source"
TARGET = "flind_wave255_events"
VIEW = "flind_wave255_materialized"
BROKER_PATTERN = re.compile(r"127\.0\.0\.1:[0-9]{4,5}\Z")


class Refused(ValueError):
    """No service should be launched if this admission fails."""


def fixture() -> list[dict]:
    if len(EVENTS) != 3 or [row["team_id"] for row in EVENTS] != [101, 202, 101]:
        raise Refused("unrecognized_original_kafka_fixture")
    if len({row["distinct_id"] for row in EVENTS}) != 1:
        raise Refused("missing_cross_team_identity_collision")
    return [
        {
            "uuid": f"00000000-0000-4000-8000-{n:012d}",
            "team_id": row["team_id"], "event": row["event"],
            "distinct_id": row["distinct_id"], "token": "flind_wave255_synthetic",
        }
        for n, row in enumerate(EVENTS, start=25501)
    ]


def require_space(min_bytes: int) -> None:
    if shutil.disk_usage(ROOT).free < min_bytes:
        raise Refused("owner_mac_disk_reserve_insufficient")


def admit(repo: Path, kafka_home: Path, asset: Path) -> str:
    require_space(FREE_START_BYTES)
    if (repo.is_symlink() or not repo.is_dir() or repo.stat().st_uid != os.getuid()
            or kafka_home.is_symlink() or not kafka_home.is_dir()
            or not (kafka_home / "bin/kafka-server-start.sh").is_file()):
        raise Refused("unowned_original_source_or_kafka")
    if (asset.is_symlink() or not asset.is_file()
            or asset.parent.parent != ROOT or asset.stat().st_uid != os.getuid()
            or asset.stat().st_size != ASSET_SIZE):
        raise Refused("unapproved_clickhouse_asset_path")
    parent = asset.parent
    marker = parent / ".flind-owner-only"
    if (parent.is_symlink() or parent.stat().st_uid != os.getuid()
            or parent.stat().st_mode & 0o077 or marker.is_symlink()
            or not marker.is_file() or marker.read_text() != ASSET_OWNER):
        raise Refused("unowned_official_clickhouse_asset")
    with asset.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != OFFICIAL_MAC_ARM64_SHA256:
            raise Refused("official_clickhouse_asset_digest_mismatch")
    try:
        commit, spec = source_clickhouse_spec(repo)
        schema_commit, columns = verified_schema(repo, "HEAD")
    except (OSError, ValueError, RuntimeError) as exc:
        raise Refused("original_source_contract_unavailable") from exc
    if commit != schema_commit or columns != EXPECTED_COLUMNS:
        raise Refused("source_hcl_contract_mismatch")
    if not version_qualified(EXPECTED_VERSION, spec):
        raise Refused("unsupported_clickhouse_version_contract")
    return commit


def sql(port: int, command: str) -> str:
    if (type(port) is not int or not 1024 <= port <= 65535
            or not command.isascii() or len(command) > 1800):
        raise Refused("unsafe_loopback_clickhouse_query")
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("POST", "/", body=command.encode("ascii"),
                           headers={"Content-Type": "text/plain"})
        response = connection.getresponse()
        body = response.read(10000)
        if response.status != 200 or len(body) == 10000:
            raise Refused("isolated_clickhouse_sql_failed")
        return body.decode("utf-8").strip()
    finally:
        connection.close()


def engine_readback(port: int, broker: str, expected: list[dict]) -> dict:
    """Actual ClickHouse Kafka engine subscription; never Python relay."""
    if not BROKER_PATTERN.fullmatch(broker):
        raise Refused("non_loopback_kafka_broker")
    if sql(port, "SELECT version()") != EXPECTED_VERSION:
        raise Refused("running_clickhouse_binary_not_supported")
    if sql(port, "SELECT name FROM system.table_engines WHERE name='Kafka'") != "Kafka":
        raise Refused("real_clickhouse_kafka_engine_missing")
    if sql(port, "SELECT name FROM system.table_engines WHERE name='MergeTree'") != "MergeTree":
        raise Refused("real_clickhouse_mergetree_engine_missing")
    created: list[tuple[str, str]] = []
    try:
        sql(port, f"CREATE TABLE {TARGET} (uuid String,team_id Int64,event String,"
            "distinct_id String,token String) ENGINE=MergeTree ORDER BY (team_id,uuid)")
        created.append(("TABLE", TARGET))
        sql(port, f"CREATE TABLE {SOURCE} (uuid String,team_id Int64,event String,"
            f"distinct_id String,token String) ENGINE=Kafka SETTINGS kafka_broker_list='{broker}',"
            f"kafka_topic_list='{TOPIC}',kafka_group_name='flind_wave255_source',"
            "kafka_format='JSONEachRow',kafka_num_consumers=1")
        created.append(("TABLE", SOURCE))
        sql(port, f"CREATE MATERIALIZED VIEW {VIEW} TO {TARGET} AS SELECT "
            f"uuid,team_id,event,distinct_id,token FROM {SOURCE}")
        created.append(("VIEW", VIEW))
        # 25.12 rejects kafka_auto_offset_reset. Publish only after the
        # Kafka engine's materialized-view subscriber is ready, so the
        # broker-default offset policy cannot skip earlier messages.
        publish(broker, expected)
        deadline = time.monotonic() + 32
        observed: list[dict] = []
        while time.monotonic() < deadline:
            require_space(FREE_FLOOR_BYTES)
            rows = sql(port, f"SELECT uuid,team_id,event,distinct_id,token "
                       f"FROM {TARGET} ORDER BY uuid FORMAT JSONEachRow")
            observed = [json.loads(line) for line in rows.splitlines() if line]
            if len(observed) >= len(expected):
                break
            time.sleep(0.6)
        if observed != sorted(expected, key=lambda row: row["uuid"]):
            raise Refused("kafka_engine_real_mergetree_readback_mismatch")
        team_counts = sql(port, f"SELECT team_id,count() FROM {TARGET} "
                              "GROUP BY team_id ORDER BY team_id")
        no_other_team = sql(port, f"SELECT count() FROM {TARGET} WHERE team_id=303")
        if team_counts != "101\t2\n202\t1" or no_other_team != "0":
            raise Refused("synthetic_team_filter_mismatch")
        parts = sql(port, "SELECT count(),sum(rows) FROM system.parts "
                          f"WHERE database='default' AND table='{TARGET}' AND active=1")
        summary = parts.split("\t")
        if (len(summary) != 2 or not all(v.isdecimal() for v in summary)
                or int(summary[0]) < 1 or int(summary[1]) != len(expected)):
            raise Refused("durable_mergetree_disk_parts_missing")
        return {
            "real_clickhouse_kafka_engine_subscription_qualified": True,
            "real_materialized_view_mergetree_rows_qualified": True,
            "disk_parts_on_actual_mergetree_verified": True,
            "three_synthetic_rows_exact": len(observed),
            "tenant_101_count": 2, "tenant_202_count": 1, "unknown_tenant_303_count": 0,
            "production_native_rust_ingest_qualified": False,
            "production_node_ingest_qualified": False,
            "authenticated_tenant_authorization_qualified": False,
            "release_qualified": False,
        }
    finally:
        for kind, name in reversed(created):
            sql(port, f"DROP {kind} IF EXISTS {name}")


def publish(broker: str, records: list[dict]) -> None:
    if not BROKER_PATTERN.fullmatch(broker) or len(records) != 3:
        raise Refused("invalid_synthetic_kafka_destination")
    from confluent_kafka import Producer
    from confluent_kafka.admin import AdminClient, NewTopic

    admin = AdminClient({"bootstrap.servers": broker, "socket.timeout.ms": 8000})
    admin.create_topics([NewTopic(TOPIC, num_partitions=1, replication_factor=1)],
                        operation_timeout=12)[TOPIC].result(timeout=16)
    producer = Producer({"bootstrap.servers": broker, "acks": "all",
                         "message.timeout.ms": 10000,
                         "client.id": "flind-wave255-synthetic-only"})
    confirmations: list[bool] = []
    for row in records:
        payload = json.dumps(row, separators=(",", ":"), sort_keys=True).encode("ascii")
        if len(payload) > 512:
            raise Refused("synthetic_message_exceeds_budget")
        producer.produce(TOPIC, value=payload, on_delivery=lambda err, msg:
                         confirmations.append(err is None))
    if producer.flush(15) or confirmations != [True, True, True]:
        raise Refused("synthetic_kafka_producer_acks_missing")


def qualify(repo: Path, kafka_home: Path, asset: Path) -> dict:
    report: dict = {
        "phase": "flind_wave255_real_kafka_engine_synthetic_only",
        "real_kafka_broker": False, "actual_clickhouse_kafka_engine_qualified": False,
        "original_rust_production_worker_qualified": False,
        "original_node_production_ingest_qualified": False,
        "authenticated_tenant_qualified": False,
        "distributed_clickhouse_migrations_qualified": False,
        "release_qualified": False,
    }
    try:
        report["source_commit"] = admit(repo, kafka_home, asset)
        fixture_rows = fixture()
        with tempfile.TemporaryDirectory(prefix="flind-wave255-engine-", dir=ROOT) as td:
            scratch = Path(td)
            runtime = scratch / "official-clickhouse-25.12"
            shutil.copyfile(asset, runtime)
            runtime.chmod(0o700)

            def broker_ready(broker: str) -> dict:
                if not BROKER_PATTERN.fullmatch(broker):
                    raise Refused("non_loopback_kafka_broker")
                require_space(FREE_BOOT_BYTES)
                boot = subprocess.run([str(runtime), "--version"],
                                      stdin=subprocess.DEVNULL, capture_output=True,
                                      check=False, timeout=45,
                                      env={**os.environ, "HOME": td})
                if boot.returncode or EXPECTED_VERSION.encode() not in boot.stdout:
                    raise Refused("official_clickhouse_bootstrap_mismatch")
                require_space(FREE_FLOOR_BYTES)
                service = ch.isolated_clickhouse(
                    binary=str(runtime),
                    on_ready=lambda port: engine_readback(port, broker, fixture_rows),
                )
                detail = service.get("event_readback") or {}
                return {
                    "actual_clickhouse_kafka_engine_qualified": (
                        service.get("isolated_clickhouse_passed") is True
                        and detail.get("real_clickhouse_kafka_engine_subscription_qualified") is True
                        and detail.get("real_materialized_view_mergetree_rows_qualified") is True
                        and detail.get("disk_parts_on_actual_mergetree_verified") is True
                    ),
                    "detail": detail,
                }

            result = qualify_kafka(kafka_home, on_broker_ready=broker_ready)
            engine = result.get("native_capture_relay") or {}
            report["real_kafka_broker"] = (
                result.get("isolated_kafka_passed") is True
                and result.get("exact_json_message_roundtrip") is True
            )
            report["actual_clickhouse_kafka_engine_qualified"] = (
                report["real_kafka_broker"]
                and engine.get("actual_clickhouse_kafka_engine_qualified") is True
            )
            if report["actual_clickhouse_kafka_engine_qualified"]:
                report["real_engine_receipt"] = engine["detail"]
            else:
                report["blocker"] = "original_ephemeral_qualifier_or_kafka_engine_failed"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as error:
        report["blocker"] = type(error).__name__ if not isinstance(error, Refused) else str(error)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--kafka-home", type=Path, required=True)
    parser.add_argument("--official-asset", type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.repo, args.kafka_home, args.official_asset)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["actual_clickhouse_kafka_engine_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
