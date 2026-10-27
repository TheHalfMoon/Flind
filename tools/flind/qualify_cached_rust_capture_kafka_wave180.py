#!/usr/bin/env python3
"""Real compiled first-party Rust Capture HTTP -> private Kafka 4.3.1 probe.

Runs only synthetic fixture traffic using dedicated Redis 7.4.11 and a private
Kafka broker borrowed from Wave179. Cached binary provenance is explicit.
No product SDK, worker, ClickHouse MV, authenticated tenant query or release.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import datetime, UTC
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import qualify as qualify_kafka_relay

REDIS7 = Path("/private/tmp/flind-wave74-services/redis-7.4.11/src/redis-server")
CAPTURE = Path("/private/tmp/flind-wave110-rust-target/debug/capture")
EXPECTED_CAPTURE_SHA256 = "a255ae78e180d9488b4efc126b7d2c8378e209640ee36d7c28f491bb40693379"
TOPIC = "flind_wave180_first_party_native_capture"
GROUP = "flind-wave180-native-synthetic"
PROBE_PATH = "/i/v1/analytics/events"
SYNTHETIC_TOKEN = "flind_synthetic_internal_token"
SYNTHETIC_ID = "flind-wave112-synthetic"


def local_port() -> int:
    with socket.socket() as conn:
        conn.bind(("127.0.0.1", 0))
        return conn.getsockname()[1]


def checked_capture() -> bool:
    if not CAPTURE.is_file() or not os.access(CAPTURE, os.X_OK):
        return False
    with CAPTURE.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return digest == EXPECTED_CAPTURE_SHA256


def admitted_native(bootstrap: str, owned: Path) -> bool:
    return (
        bool(re.fullmatch(r"127\.0\.0\.1:[0-9]{4,5}", bootstrap))
        and owned.is_dir() and not owned.is_symlink()
        and owned.parent.is_dir() and owned.parent.parent == Path("/private/tmp")
        and (owned / ".flind-wave179-owned").is_file()
        and (owned / ".flind-wave179-owned").read_text()
        == "FLIND_WAVE179_SCRATCH_V1\n"
        and checked_capture()
        and REDIS7.is_file() and os.access(REDIS7, os.X_OK)
    )


def stop_owned(child: subprocess.Popen | None) -> bool:
    if child is None:
        return True
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
    return child.poll() is not None


def synthetic_http_event(port: int) -> tuple[str, bool, int]:
    uid = str(uuid4())
    stamp = datetime.now(UTC).isoformat()
    data = json.dumps({
        "created_at": stamp,
        "capture_internal": True,
        "historical_migration": False,
        "batch": [{
            "uuid": uid, "distinct_id": SYNTHETIC_ID,
            "event": "$pageview", "timestamp": stamp,
            "properties": {"$geoip_disable": True, "$pathname": "/synthetic"},
        }],
    }, separators=(",", ":")).encode()
    conn = HTTPConnection("127.0.0.1", port, timeout=4)
    try:
        conn.request("POST", PROBE_PATH, body=data, headers={
            "Authorization": "Bearer " + SYNTHETIC_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "flind-wave180-native/1.0",
            "PostHog-Sdk-Info": "flind-wave180-native/1.0",
            "PostHog-Attempt": "1",
            "PostHog-Request-Id": str(uuid4()),
            "PostHog-Request-Timestamp": stamp,
        })
        response = conn.getresponse()
        body = response.read(4097)
        if len(body) > 4096:
            raise ValueError("unbounded_capture_ack_response")
        try:
            ack = json.loads(body)
        except (UnicodeError, ValueError):
            ack = {}
        return uid, (
            response.status == 200
            and isinstance(ack, dict)
            and ack.get("results", {}).get(uid, {}).get("result") == "ok"
        ), response.status
    finally:
        conn.close()


def read_native_event(bootstrap: str, expected_id: str) -> dict:
    from confluent_kafka import Consumer
    consumer = Consumer({
        "bootstrap.servers": bootstrap,
        "group.id": GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "session.timeout.ms": 7000,
        "client.id": "flind-wave180-native-consumer",
    })
    try:
        consumer.subscribe([TOPIC])
        end = time.monotonic() + 18
        messages = []
        while time.monotonic() < end and len(messages) < 1:
            msg = consumer.poll(0.7)
            if msg is None:
                continue
            if msg.error():
                raise RuntimeError("native_capture_kafka_consumer_error")
            payload = msg.value()
            if not isinstance(payload, bytes) or len(payload) > 65536:
                raise ValueError("unbounded_native_kafka_event")
            event = json.loads(payload)
            messages.append(event)
        if len(messages) != 1:
            raise ValueError("native_kafka_event_not_received")
        event = messages[0]
        if (type(event) is not dict
                or event.get("uuid") != expected_id
                or event.get("event") != "$pageview"
                or event.get("distinct_id") != SYNTHETIC_ID
                or event.get("token") != SYNTHETIC_TOKEN):
            raise ValueError("native_kafka_uuid_or_payload_mismatch")
        consumer.commit(asynchronous=False)
        return event
    finally:
        consumer.close()


def private_capture_probe(
    bootstrap: str, owned: Path,
    *, on_native_event: Callable[[dict, str], dict[str, object]] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "real_cached_rust_capture_http_qualified": False,
        "native_capture_acknowledged": False,
        "native_kafka_uuid_readback_qualified": False,
        "native_redis_supported_version_qualified": False,
        "first_party_ingestion_worker_qualified": False,
        "production_clickhouse_ingestion_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    redis_proc: subprocess.Popen | None = None
    capture_proc: subprocess.Popen | None = None
    try:
        if not admitted_native(bootstrap, owned):
            raise ValueError("unapproved_native_cached_binary_or_kafka_target")
        # Consume exactly one native-generated event; only fixed sandbox topic.
        from confluent_kafka.admin import AdminClient, NewTopic
        admin = AdminClient({"bootstrap.servers": bootstrap,
                             "socket.timeout.ms": 8000})
        new = admin.create_topics([NewTopic(TOPIC, 1, 1)], operation_timeout=10)
        new[TOPIC].result(timeout=16)
        redis_port, capture_port = local_port(), local_port()
        if redis_port == capture_port:
            raise ValueError("scratch_local_port_collision")
        native_dir = owned / "native-capture-wave180"
        if native_dir.exists() or native_dir.is_symlink():
            raise ValueError("native_capture_scratch_conflict")
        native_dir.mkdir()
        with (native_dir / "redis.out").open("wb") as redis_log, (
            native_dir / "capture.out"
        ).open("wb") as capture_log:
            redis_proc = subprocess.Popen([
                str(REDIS7), "--bind", "127.0.0.1", "--port", str(redis_port),
                "--save", "", "--appendonly", "no", "--protected-mode", "yes",
                "--maxmemory", "32mb", "--loglevel", "warning",
                "--dir", str(native_dir),
            ], cwd=native_dir, stdin=subprocess.DEVNULL, stdout=redis_log,
                stderr=subprocess.STDOUT,
                env={"PATH": "/usr/bin:/bin", "HOME": str(native_dir), "LANG": "C"})
            ready = False
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and redis_proc.poll() is None:
                try:
                    with socket.create_connection(("127.0.0.1", redis_port), timeout=0.3):
                        ready = True
                        break
                except OSError:
                    time.sleep(0.12)
            if not ready:
                raise RuntimeError("scratch_redis7_not_ready")
            result["native_redis_supported_version_qualified"] = True
            env = {
                "PATH": "/usr/bin:/bin", "HOME": str(native_dir), "LANG": "C",
                "REDIS_URL": f"redis://127.0.0.1:{redis_port}/",
                "ADDRESS": f"127.0.0.1:{capture_port}",
                "KAFKA_HOSTS": bootstrap,
                "KAFKA_INGESTION_PRODUCER_METADATA_BROKER_LIST": bootstrap,
                "KAFKA_INGESTION_PRODUCER_LINGER_MS": "0",
                "KAFKA_INGESTION_PRODUCER_MESSAGE_TIMEOUT_MS": "9000",
                "CAPTURE_OUTPUT_ANALYTICS_MAIN_TOPIC": TOPIC,
                "NOOP_SINK": "false",
                "PRINT_SINK": "false",
                "CAPTURE_MODE": "events",
                "EXPORT_PROMETHEUS": "false",
                "GLOBAL_RATE_LIMIT_ENABLED": "false",
                "OVERFLOW_ENABLED": "false",
                "CAPTURE_INGESTION_WARNINGS_ENABLED": "false",
                "OTEL_SERVICE_NAME": "flind-wave180-synthetic-native",
                "RUST_LOG": "warn",
            }
            capture_proc = subprocess.Popen(
                [str(CAPTURE)], cwd=native_dir, env=env,
                stdin=subprocess.DEVNULL, stdout=capture_log,
                stderr=subprocess.STDOUT,
            )
            ready = False
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and capture_proc.poll() is None:
                try:
                    with socket.create_connection(("127.0.0.1", capture_port), timeout=0.3):
                        ready = True
                        break
                except OSError:
                    time.sleep(0.13)
            if not ready:
                raise RuntimeError("scratch_native_rust_capture_not_listening")
            uid, ack, status = synthetic_http_event(capture_port)
            result["native_http_status"] = status
            if not ack:
                raise ValueError("native_capture_http_ack_missing")
            result["native_capture_acknowledged"] = True
            native = read_native_event(bootstrap, uid)
            result["native_kafka_uuid_readback_qualified"] = (
                native.get("uuid") == uid
            )
            result["real_cached_rust_capture_http_qualified"] = (
                result["native_capture_acknowledged"]
                and result["native_kafka_uuid_readback_qualified"]
            )
            result["cached_capture_binary_sha256"] = EXPECTED_CAPTURE_SHA256
            # Callback receives only an ACKed, exact-UUID Kafka record after
            # synthetic fixture validation. It runs while this private broker
            # still exists, without upgrading product/release qualification.
            if on_native_event is not None:
                downstream = on_native_event(native, uid)
                if not isinstance(downstream, dict):
                    raise ValueError("invalid_native_clickhouse_callback_receipt")
                result["optional_native_downstream"] = downstream
    except Exception as exc:
        result["blocker"] = type(exc).__name__
        # These are closed-set refusal codes from the synthetic-only Wave182
        # adapter. Do not serialize the Kafka payload or arbitrary exception.
        allowed_codes = {
            "invalid_native_event", "invalid_acknowledged_uuid",
            "native_event_not_exact_synthetic_fixture",
            "client_supplied_tenant_identifier", "unbounded_native_properties",
            "bad_native_properties_json", "native_fixture_path_mismatch",
            "native_properties_not_an_object",
            "first_party_event_schema_changed", "native_clickhouse_scratch_conflict",
            "native_clickhouse_execution_blocked", "native_clickhouse_sql_failed",
            "invalid_native_clickhouse_readback",
            "native_uuid_not_stored_or_cross_team_leak",
        }
        if type(exc).__name__ == "NativeRelayRejected" and str(exc) in allowed_codes:
            result["synthetic_callback_refusal_code"] = str(exc)
    finally:
        result["owned_capture_stopped"] = stop_owned(capture_proc)
        result["owned_redis7_stopped"] = stop_owned(redis_proc)
    return result


def qualify(repo: Path, kafka_home: Path, scratch: Path) -> dict[str, object]:
    # Owns Kafka4.3.1 as well as the native child processes and deletes the
    # marked broker scratch after all callbacks have finished.
    base = qualify_kafka_relay(
        repo, kafka_home, scratch,
        on_broker_ready=private_capture_probe,
    )
    native = base.get("optional_private_kafka_probe") or {}
    result = {
        "phase": "first-party-cached-rust-capture-http-to-real-private-kafka",
        "real_kafka_to_clickhouse_python_relay_qualified":
            base.get("local_clickhouse_relay_qualified") is True,
        "cached_rust_capture_to_real_kafka_qualified": bool(
            native.get("real_cached_rust_capture_http_qualified")
            and native.get("native_kafka_uuid_readback_qualified")
            and native.get("owned_capture_stopped")
            and native.get("owned_redis7_stopped")
            and base.get("owned_kafka_process_stopped")
            and base.get("owned_kafka_scratch_removed")
        ),
        "native_capture_receipt": native,
        "kafka_qualified": base.get("kafka_431_broker_qualified") is True,
        "redis7_supported_for_flind": native.get(
            "native_redis_supported_version_qualified") is True,
        "first_party_ingestion_consumer_qualified": False,
        "clickhouse_materialized_ingestion_qualified": False,
        "flind_sdk_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "dashboard_qualified": False,
        "release_qualified": False,
        "source_commit": base.get("source_commit"),
        "owned_kafka_process_stopped": base.get("owned_kafka_process_stopped"),
        "owned_kafka_scratch_removed": base.get("owned_kafka_scratch_removed"),
    }
    if not result["cached_rust_capture_to_real_kafka_qualified"]:
        result["blocker"] = native.get("blocker") or base.get("blocker") or "native_rust_capture_not_qualified"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--kafka-home", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    receipt = qualify(args.repo, args.kafka_home, args.scratch)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print("Flind native Rust HTTP → private Kafka:",
              "PASS" if receipt["cached_rust_capture_to_real_kafka_qualified"] else "BLOCKED")
    return 0 if receipt["cached_rust_capture_to_real_kafka_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
