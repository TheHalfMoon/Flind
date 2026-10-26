#!/usr/bin/env python3
"""Native Rust Capture → Kafka 4.3.1 → actual Node TypeScript deserializer.

This validates real synthetic Kafka *event data* crossing into the first
production Node adapter function, but it does NOT start the Rust gRPC
consumer/API, Node worker, product ClickHouse schema or dashboard.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from tools.flind.qualify_ephemeral_kafka_wave84 import qualify_kafka
from tools.flind.qualify_native_capture_kafka_wave113 import (
    DEFAULT_HOME, CAPTURE, REDIS, TOPIC, real_native_roundtrip,
)

ROOT = Path(__file__).resolve().parents[2]
NODE_SCRIPT = ROOT / "tools/flind/inspect_node_kafka_event_wave116.mjs"


def node_adapter_receipt(bootstrap: str, event: dict) -> dict:
    base = {
        "native_kafka_event_node_adapter_passed": False,
        "production_ingestion_worker_started": False,
        "real_rust_grpc_consumer_qualified": False,
        "product_clickhouse_event_schema_qualified": False,
        "authenticated_query_api_qualified": False,
        "dashboard_e2e_qualified": False,
        "release_qualified": False,
    }
    if not (
        isinstance(bootstrap, str)
        and bootstrap.startswith("127.0.0.1:")
        and isinstance(event, dict)
        and event.get("event") == "$pageview"
        and event.get("distinct_id") == "flind-wave112-synthetic"
        and event.get("token") == "flind_synthetic_internal_token"
        and NODE_SCRIPT.is_file()
        and shutil.which("node")
    ):
        return {**base, "blocker": "Untrusted or unavailable native Kafka Node fixture"}

    payload = json.dumps({"topic": TOPIC, "event": event}, ensure_ascii=False)
    if len(payload.encode("utf8")) > 32_000:
        return {**base, "blocker": "Native Kafka event exceeded bounded Node fixture"}
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C",
        # Avoid automatically importing workspace tooling or paid services.
        "NODE_OPTIONS": "",
    }
    try:
        process = subprocess.run(
            ["node", "--no-warnings", "--experimental-strip-types", str(NODE_SCRIPT)],
            input=payload, text=True, cwd=ROOT, env=env,
            capture_output=True, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {**base, "blocker": "Native Node process unavailable"}
    if process.returncode != 0 or len(process.stdout) > 2500:
        # The Node script emits only fixed diagnostic strings, never a token
        # or a raw payload. Do not expose arbitrary stderr in a report.
        known = ("not the expected native synthetic Capture event", "real production deserializer misread synthetic Kafka record", "event fixture missing", "invalid fixture envelope")
        reason = next((x for x in known if x in process.stderr), "Runtime Node adapter unavailable")
        return {**base, "blocker": reason}
    try:
        result = json.loads(process.stdout)
    except ValueError:
        return {**base, "blocker": "Node adapter receipt invalid"}
    valid = (
        result.get("source_record_was_native_rust_kafka") is True
        and result.get("production_typescript_deserializer_executed") is True
        and result.get("uuid_preserved_in_node_buffer") is True
        and result.get("token_and_distinct_id_preserved") is True
        and result.get("actual_node_ingestion_worker_qualified") is False
        and result.get("actual_rust_ingestion_consumer_api_qualified") is False
        and result.get("release_qualified") is False
    )
    return {
        **base,
        "native_kafka_event_node_adapter_passed": valid,
        "production_typescript_deserializer_executed": valid,
        "uuid_preserved_in_node_buffer": valid,
        **({"blocker": "Node adapter rejected Kafka record"} if not valid else {}),
    }


def qualify() -> dict:
    base = {
        "real_rust_capture_to_kafka_to_node_adapter": False,
        "real_kafka_431_broker": False,
        "native_rust_to_kafka_uuid_verified": False,
        "production_node_ingestion_worker_qualified": False,
        "real_rust_grpc_consumer_api_qualified": False,
        "real_production_clickhouse_ingestion_qualified": False,
        "tenant_query_api_qualified": False,
        "browser_dashboard_e2e_qualified": False,
        "release_qualified": False,
    }
    if not CAPTURE.is_file() or not REDIS.is_file() or not DEFAULT_HOME.is_dir():
        return {**base, "blocker": "Native Rust Capture, Redis or Kafka unavailable"}
    if shutil.disk_usage("/tmp").free < 10 * 1024**3:
        return {**base, "blocker": "Disk reserve lower than 10 GiB"}
    try:
        broker = qualify_kafka(
            DEFAULT_HOME,
            on_broker_ready=lambda bootstrap: real_native_roundtrip(
                bootstrap, DEFAULT_HOME, on_native_consumed=node_adapter_receipt
            ),
        )
        native = broker.get("native_capture_relay") or {}
        child = native.get("native_downstream_probe") or {}
        passed = (
            broker.get("isolated_kafka_passed") is True
            and native.get("actual_native_capture_kafka_roundtrip") is True
            and native.get("owned_capture_stopped") is True
            and native.get("owned_redis_stopped") is True
            and child.get("native_kafka_event_node_adapter_passed") is True
        )
        return {
            **base,
            "real_rust_capture_to_kafka_to_node_adapter": passed,
            "real_kafka_431_broker": broker.get("isolated_kafka_passed") is True,
            "native_rust_to_kafka_uuid_verified": native.get("actual_native_capture_kafka_roundtrip") is True,
            "node_adapter_receipt": child,
            **({"blocker": child.get("blocker") or native.get("blocker")
                or broker.get("blocker") or "Real Node bridge not qualified"} if not passed else {}),
        }
    except (OSError, subprocess.SubprocessError, ValueError):
        return {**base, "blocker": "Native Rust Kafka Node test failed"}


if __name__ == "__main__":
    report = qualify()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["real_rust_capture_to_kafka_to_node_adapter"] else 2)
