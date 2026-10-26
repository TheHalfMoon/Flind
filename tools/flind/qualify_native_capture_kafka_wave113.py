#!/usr/bin/env python3
"""Real native Rust Capture -> private Kafka 4.3 broker -> consumer readback.

Not a synthetic CLI producer. Captured event must be exactly the UUID the
actual Rust HTTP server acknowledged. No ClickHouse or product API here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from uuid import uuid4

from tools.flind.qualify_ephemeral_kafka_wave84 import (
    kafka_paths, qualify_kafka,
)
from tools.flind.qualify_native_capture_server_wave111 import (
    CAPTURE, REDIS, unused_port, terminate, synthetic_noop_event, http,
)

TOPIC = "flind-wave113-native-analytics"
DEFAULT_HOME = Path("/tmp/flind-kafka-4.3.1/kafka_2.13-4.3.1")


def refused(reason: str) -> dict:
    return {
        "actual_native_capture_kafka_roundtrip": False,
        "native_rust_http_bound": False,
        "native_event_ack_ok": False,
        "native_event_uuid_read_back_from_kafka": False,
        "private_kafka_431_broker": False,
        "real_redis_local": False,
        "synthetic_fixture_only": True,
        "no_noop_sink": True,
        "production_clickhouse_ingestion": False,
        "production_query_api": False,
        "tenant_auth_end_to_end": False,
        "dashboard_browser_e2e": False,
        "release_qualified": False,
        "blocker": reason,
    }


def kafka_cli_env(folder: str) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": folder, "TMPDIR": folder, "LANG": "C",
        "KAFKA_HEAP_OPTS": "-Xms128m -Xmx256m",
        "JAVA_TOOL_OPTIONS": "-Djava.awt.headless=true",
        "LOG_DIR": folder,
    }
    if os.environ.get("JAVA_HOME"):
        env["JAVA_HOME"] = os.environ["JAVA_HOME"]
    return env


def run_cli(args: list[str], env: dict[str, str], *, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(args, env=env, capture_output=True, text=True,
                          timeout=timeout, check=False)


def real_native_roundtrip(bootstrap: str, kafka_home: Path) -> dict:
    receipt = refused("Native Rust -> Kafka event unavailable")
    if not CAPTURE.is_file() or not REDIS.is_file():
        receipt["blocker"] = "Native Capture or Redis binary missing"
        return receipt
    if shutil.disk_usage("/tmp").free < 10 * 1024**3:
        receipt["blocker"] = "10 GiB free-disk reserve required"
        return receipt
    try:
        bins = kafka_paths(kafka_home)
    except (OSError, ValueError):
        receipt["blocker"] = "Kafka client binaries unavailable"
        return receipt
    with tempfile.TemporaryDirectory(prefix="flind-native-kafka-") as folder:
        cli_env = kafka_cli_env(folder)
        redis_port = unused_port()
        capture_port = unused_port()
        while capture_port == redis_port:
            capture_port = unused_port()
        redis_proc = capture_proc = None
        try:
            created = run_cli([
                str(bins["topics"]), "--bootstrap-server", bootstrap,
                "--create", "--topic", TOPIC,
                "--partitions", "1", "--replication-factor", "1",
            ], cli_env, timeout=28)
            if created.returncode:
                receipt["blocker"] = "Isolated Kafka topic creation failed"
                return receipt
            receipt["private_kafka_431_broker"] = True
            with open(Path(folder) / "redis.out", "wb") as redis_log, open(
                Path(folder) / "capture.out", "wb"
            ) as capture_log:
                redis_proc = subprocess.Popen([
                    str(REDIS), "--bind", "127.0.0.1", "--port", str(redis_port),
                    "--save", "", "--appendonly", "no", "--protected-mode", "yes",
                    "--maxmemory", "32mb", "--loglevel", "warning",
                ], cwd=folder,
                    env={"PATH": "/usr/bin:/bin", "HOME": folder, "LANG": "C"},
                    stdin=subprocess.DEVNULL, stdout=redis_log,
                    stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and redis_proc.poll() is None:
                    try:
                        with socket.create_connection(("127.0.0.1", redis_port), timeout=0.3):
                            receipt["real_redis_local"] = True
                            break
                    except OSError:
                        time.sleep(0.12)
                if not receipt["real_redis_local"]:
                    receipt["blocker"] = "Redis did not accept loopback connection"
                    return receipt
                env = {
                    "PATH": "/usr/bin:/bin", "HOME": folder, "LANG": "C",
                    "REDIS_URL": f"redis://127.0.0.1:{redis_port}/",
                    "ADDRESS": f"127.0.0.1:{capture_port}",
                    "KAFKA_HOSTS": bootstrap,
                    "KAFKA_INGESTION_PRODUCER_METADATA_BROKER_LIST": bootstrap,
                    "KAFKA_INGESTION_PRODUCER_LINGER_MS": "0",
                    "KAFKA_INGESTION_PRODUCER_MESSAGE_TIMEOUT_MS": "9000",
                    "CAPTURE_OUTPUT_ANALYTICS_MAIN_TOPIC": TOPIC,
                    "NOOP_SINK": "false", "PRINT_SINK": "false",
                    "CAPTURE_MODE": "events",
                    "EXPORT_PROMETHEUS": "false",
                    "GLOBAL_RATE_LIMIT_ENABLED": "false",
                    "OVERFLOW_ENABLED": "false",
                    "CAPTURE_INGESTION_WARNINGS_ENABLED": "false",
                    "OTEL_SERVICE_NAME": "flind-native-kafka-test",
                    "RUST_LOG": "warn",
                }
                capture_proc = subprocess.Popen([str(CAPTURE)],
                    cwd=folder, env=env, stdin=subprocess.DEVNULL,
                    stdout=capture_log, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and capture_proc.poll() is None:
                    try:
                        with socket.create_connection(("127.0.0.1", capture_port), timeout=0.3):
                            receipt["native_rust_http_bound"] = True
                            break
                    except OSError:
                        time.sleep(0.12)
                if not receipt["native_rust_http_bound"]:
                    receipt["blocker"] = "Native Kafka-sink Rust Capture did not start"
                    return receipt
                live = None
                for _ in range(10):
                    try:
                        live, _ = http("/_liveness", capture_port)
                        if live == 200:
                            break
                    except OSError:
                        time.sleep(0.15)
                if live != 200:
                    receipt["blocker"] = "Native Rust liveness check refused"
                    return receipt
                sent = synthetic_noop_event(capture_port)
                receipt["native_http_status"] = sent.get("synthetic_noop_http_status")
                receipt["native_event_ack_ok"] = sent.get("native_synthetic_noop_acknowledged") is True
                if not receipt["native_event_ack_ok"]:
                    receipt["blocker"] = "Rust Capture did not ACK synthetic event"
                    return receipt
                received = run_cli([
                    str(bins["console-consumer"]), "--bootstrap-server", bootstrap,
                    "--topic", TOPIC, "--from-beginning", "--max-messages", "1",
                    "--timeout-ms", "15000",
                ], cli_env, timeout=35)
                if received.returncode:
                    receipt["blocker"] = "Actual Kafka consumer timed out"
                    return receipt
                lines = [row for row in received.stdout.splitlines() if row.startswith("{")]
                if len(lines) != 1:
                    receipt["blocker"] = "Kafka native event count did not equal one"
                    return receipt
                event = json.loads(lines[0])
                receipt["native_event_uuid_read_back_from_kafka"] = (
                    isinstance(event, dict)
                    and event.get("uuid") == sent.get("synthetic_event_uuid")
                    and event.get("event") == "$pageview"
                    and event.get("distinct_id") == "flind-wave112-synthetic"
                    and event.get("token") == "flind_synthetic_internal_token"
                )
                receipt["actual_native_capture_kafka_roundtrip"] = (
                    receipt["native_rust_http_bound"]
                    and receipt["native_event_ack_ok"]
                    and receipt["native_event_uuid_read_back_from_kafka"]
                )
                if receipt["actual_native_capture_kafka_roundtrip"]:
                    receipt.pop("blocker", None)
                return receipt
        except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError):
            receipt["blocker"] = "Bounded native Capture Kafka proof unavailable"
            return receipt
        finally:
            terminate(capture_proc)
            terminate(redis_proc)
            receipt["owned_capture_stopped"] = capture_proc is None or capture_proc.poll() is not None
            receipt["owned_redis_stopped"] = redis_proc is None or redis_proc.poll() is not None


def qualify(kafka_home: Path) -> dict:
    try:
        kafka = qualify_kafka(
            kafka_home,
            on_broker_ready=lambda bootstrap: real_native_roundtrip(bootstrap, kafka_home),
        )
        native = kafka.get("native_capture_relay") or {}
        real = (
            kafka.get("isolated_kafka_passed") is True
            and native.get("actual_native_capture_kafka_roundtrip") is True
            and native.get("owned_capture_stopped") is True
            and native.get("owned_redis_stopped") is True
        )
        return {
            "actual_native_rust_capture_to_real_kafka": real,
            "isolated_kafka_431_passed": kafka.get("isolated_kafka_passed") is True,
            "native_capture_receipt": native,
            "synthetic_fixture_only": True,
            "production_clickhouse_ingestion": False,
            "production_query_api": False,
            "tenant_auth_end_to_end": False,
            "dashboard_browser_e2e": False,
            "release_qualified": False,
            **({"blocker": kafka.get("blocker", native.get("blocker", "Native Kafka proof failed"))}
               if not real else {}),
        }
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        return refused("Native Kafka 4.3.1 probe unavailable")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kafka-home", type=Path, default=DEFAULT_HOME)
    args = p.parse_args()
    report = qualify(args.kafka_home)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report.get("actual_native_rust_capture_to_real_kafka") else 2)
