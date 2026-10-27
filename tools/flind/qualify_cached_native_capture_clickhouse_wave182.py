#!/usr/bin/env python3
"""Actual cached Rust Capture HTTP -> Kafka -> ClickHouse 25.12 UUID proof.

A strict synthetic-only Python bridge consumes the exact ACKed Kafka record;
this does not run the native ingestion consumer/Node worker or a durable MV.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_cached_rust_capture_kafka_wave180 import (
    SYNTHETIC_TOKEN, SYNTHETIC_ID, checked_capture, private_capture_probe,
)
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import qualify as isolated_kafka
from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import (
    EXPECTED_COLUMNS, FIELDS, checked_scratch, verified_schema, scoped_sql,
)
from tools.flind.qualify_local_clickhouse_insert_wave178 import insert_sql
from tools.flind.qualify_supported_clickhouse_kafka_wave181 import (
    source_clickhouse_spec, binary_clickhouse_version, version_qualified,
)

SUPPORTED_CH_BINARY = Path("/private/tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64")
SYNTHETIC_TEAM_FOR_FIXED_TOKEN = 101  # test fixture only; NEVER production tenant auth


class NativeRelayRejected(ValueError):
    pass


def source_event_row(event: dict, acknowledged_uuid: str) -> dict[str, object]:
    """Permit only exact previously authenticated synthetic native event.

    Never infer a real tenant from a client-controlled Kafka field/token.
    Fixed synthetic token→numeric team mapping is only for the smoke fixture.
    """
    if type(event) is not dict:
        raise NativeRelayRejected("invalid_native_event")
    try:
        uid = str(UUID(acknowledged_uuid))
    except (TypeError, ValueError, AttributeError) as exc:
        raise NativeRelayRejected("invalid_acknowledged_uuid") from exc
    if (event.get("uuid") != uid
            or event.get("token") != SYNTHETIC_TOKEN
            or event.get("distinct_id") != SYNTHETIC_ID
            or event.get("event") != "$pageview"):
        raise NativeRelayRejected("native_event_not_exact_synthetic_fixture")
    if "team_id" in event:
        # Explicitly refuse a client-supplied numeric team; no authority here.
        raise NativeRelayRejected("client_supplied_tenant_identifier")
    props = event.get("properties")
    if isinstance(props, str):
        if len(props) > 16384:
            raise NativeRelayRejected("unbounded_native_properties")
        try:
            props = json.loads(props)
        except ValueError as exc:
            raise NativeRelayRejected("bad_native_properties_json") from exc
    if props is None:
        # The original Capture Kafka envelope may omit serialized optional
        # properties: store an empty projection rather than inventing values.
        props = {}
    if type(props) is not dict:
        raise NativeRelayRejected("native_properties_not_an_object")
    pathname = props.get("$pathname")
    # Rust Capture may normalize away optional properties. Do not invent an
    # original path. A present path must still be the synthetic fixture.
    if pathname is not None and pathname != "/synthetic":
        raise NativeRelayRejected("native_fixture_path_mismatch")
    if len(json.dumps(props)) > 16384:
        raise NativeRelayRejected("unbounded_native_properties")
    projected_properties = {"$pathname": pathname} if pathname is not None else {}
    return {
        "uuid": uid,
        "event": "$pageview",
        "properties": json.dumps(projected_properties, separators=(",", ":")),
        "timestamp": "2026-10-27 12:00:00.000000",
        "team_id": SYNTHETIC_TEAM_FOR_FIXED_TOKEN,
        "distinct_id": SYNTHETIC_ID,
    }


def store_native_event(repo: Path, scratch: Path, event: dict, ack_uuid: str,
                       clickhouse: Path) -> dict[str, object]:
    row = source_event_row(event, ack_uuid)
    _, schema = verified_schema(repo, "HEAD")
    if schema != EXPECTED_COLUMNS:
        raise NativeRelayRejected("first_party_event_schema_changed")
    ddl = ", ".join(f"{name} {schema[name]}" for name in FIELDS)
    statements = [
        f"CREATE TABLE events ({ddl}) ENGINE = Memory",
        insert_sql([row], schema),
        scoped_sql(101, kind="counts"),
        scoped_sql(202, kind="counts"),
        "SELECT uuid, team_id, event FROM events WHERE team_id=101 FORMAT JSONEachRow",
    ]
    session = scratch / "wave182-native-event-engine"
    stdout = scratch / "wave182-native-event-output.jsonl"
    stderr = scratch / "wave182-native-event-error.log"
    if any(p.exists() or p.is_symlink() for p in (session, stdout, stderr)):
        raise NativeRelayRejected("native_clickhouse_scratch_conflict")
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            proc = subprocess.run(
                [str(clickhouse), "local", "--multiquery", "--path", str(session),
                 "--max_memory_usage=134217728",
                 "--query", ";\n".join(statements) + ";\n"],
                cwd=scratch, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                check=False, timeout=22, env={**os.environ, "HOME": str(scratch)},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NativeRelayRejected("native_clickhouse_execution_blocked") from exc
    if proc.returncode or stdout.stat().st_size > 30000:
        raise NativeRelayRejected("native_clickhouse_sql_failed")
    try:
        output = [json.loads(line) for line in stdout.read_text().splitlines() if line]
    except (ValueError, UnicodeError) as exc:
        raise NativeRelayRejected("invalid_native_clickhouse_readback") from exc
    expected = [
        {"team_id": 101, "event_count": 1},
        {"uuid": ack_uuid, "team_id": 101, "event": "$pageview"},
    ]
    if output != expected:
        raise NativeRelayRejected("native_uuid_not_stored_or_cross_team_leak")
    return {
        "native_capture_ack_uuid_stored_in_clickhouse": True,
        "native_clickhouse_uuid_exact_match": True,
        "native_event_inserted_rows": 1,
        "native_clickhouse_team_101_count": 1,
        "native_clickhouse_team_202_count": 0,
        "synthetic_team_fixture_only": True,
        "first_party_ingestion_consumer_executed": False,
        "persistent_clickhouse_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }


def qualify(repo: Path, kafka_home: Path, scratch: Path,
            clickhouse: Path = SUPPORTED_CH_BINARY) -> dict[str, object]:
    receipt: dict[str, object] = {
        "phase": "cached-rust-capture-http-kafka-native-uuid-to-supported-clickhouse-memory",
        "native_capture_http_kafka_clickhouse_uuid_pass": False,
        "native_rust_consumer_qualified": False,
        "node_grpc_worker_qualified": False,
        "durable_clickhouse_ingestion_qualified": False,
        "flind_sdk_dashboard_e2e_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    try:
        checked_scratch(repo, scratch, "HEAD")
        source_commit, requirement = source_clickhouse_spec(repo)
        clickhouse_version = binary_clickhouse_version(clickhouse)
        receipt["source_commit"] = source_commit
        receipt["source_supported_clickhouse_version"] = clickhouse_version
        if not version_qualified(clickhouse_version, requirement):
            raise NativeRelayRejected("clickhouse_outside_first_party_supported_range")
        if not checked_capture():
            raise NativeRelayRejected("unverified_cached_rust_capture_binary")
        # Reuse one isolated broker. Wave179's synthetic fixture and the Rust
        # generated UUID are deliberately verified separately.
        result = isolated_kafka(
            repo, kafka_home, scratch, clickhouse=str(clickhouse),
            on_broker_ready=lambda bootstrap, owned: private_capture_probe(
                bootstrap, owned, on_native_event=lambda event, uuid: store_native_event(
                    repo, scratch, event, uuid, clickhouse,
                ),
            ),
        )
        native = result.get("optional_private_kafka_probe") or {}
        downstream = native.get("optional_native_downstream") or {}
        receipt["owned_kafka_process_stopped"] = result.get("owned_kafka_process_stopped") is True
        receipt["owned_kafka_scratch_removed"] = result.get("owned_kafka_scratch_removed") is True
        receipt["owned_capture_stopped"] = native.get("owned_capture_stopped") is True
        receipt["owned_redis7_stopped"] = native.get("owned_redis7_stopped") is True
        receipt["native_capture_http_kafka_clickhouse_uuid_pass"] = all((
            result.get("local_clickhouse_relay_qualified") is True,
            native.get("real_cached_rust_capture_http_qualified") is True,
            native.get("native_kafka_uuid_readback_qualified") is True,
            downstream.get("native_capture_ack_uuid_stored_in_clickhouse") is True,
            downstream.get("native_clickhouse_uuid_exact_match") is True,
            receipt["owned_kafka_process_stopped"],
            receipt["owned_kafka_scratch_removed"],
            receipt["owned_capture_stopped"],
            receipt["owned_redis7_stopped"],
        ))
        receipt["native_event_inserted_rows"] = downstream.get("native_event_inserted_rows", 0)
        if native.get("synthetic_callback_refusal_code"):
            receipt["synthetic_callback_refusal_code"] = native["synthetic_callback_refusal_code"]
        if not receipt["native_capture_http_kafka_clickhouse_uuid_pass"]:
            raise NativeRelayRejected(native.get("blocker") or result.get("blocker") or "native_event_uuid_readback_failed")
    except (NativeRelayRejected, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        receipt["blocker"] = str(exc) if isinstance(exc, NativeRelayRejected) else type(exc).__name__
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--kafka-home", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--clickhouse", type=Path, default=SUPPORTED_CH_BINARY)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    receipt = qualify(args.repo, args.kafka_home, args.scratch, args.clickhouse)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print("Flind cached Rust Capture→Kafka→ClickHouse UUID:",
              "PASS" if receipt["native_capture_http_kafka_clickhouse_uuid_pass"] else "BLOCKED")
    return 0 if receipt["native_capture_http_kafka_clickhouse_uuid_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
