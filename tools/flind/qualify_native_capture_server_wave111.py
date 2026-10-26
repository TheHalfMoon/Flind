#!/usr/bin/env python3
"""Run the ACTUAL compiled Capture server + isolated local Redis; never Kafka.

This is a limited real HTTP/router/health smoke test, NOT successful event
ingestion or product-readiness evidence. All subprocesses and data ephemeral.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = Path(os.environ.get("FLIND_CAPTURE_BINARY") or ROOT / "rust/target/debug/capture")
REDIS = Path(
    os.environ.get("FLIND_REDIS_BINARY") or shutil.which("redis-server")
    or "/tmp/flind-wave74-services/redis-7.4.11/src/redis-server"
)
EXPECTED = "/i/v1/analytics/events"


def unused_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def terminate(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=4)


def http(path: str, port: int, method: str = "GET", body: bytes | None = None):
    conn = HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        data = res.read(2048)
        return res.status, len(data)
    finally:
        conn.close()


def synthetic_noop_event(port: int) -> dict:
    """Exercise real Rust parsing/routing only; the output sink is explicitly NOOP."""
    uid = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()
    payload = json.dumps({
        "created_at": timestamp,
        "capture_internal": True,
        "historical_migration": False,
        "batch": [{
            "uuid": uid, "distinct_id": "flind-wave112-synthetic",
            "event": "$pageview", "timestamp": timestamp,
            "properties": {"$geoip_disable": True, "$pathname": "/synthetic"},
        }],
    }).encode()
    conn = HTTPConnection("127.0.0.1", port, timeout=4)
    try:
        conn.request("POST", EXPECTED, body=payload, headers={
            "Authorization": "Bearer flind_synthetic_internal_token",
            "Content-Type": "application/json",
            "User-Agent": "flind-capture-v1-internal/1.0",
            "PostHog-Sdk-Info": "flind-capture-v1-internal/1.0",
            "PostHog-Attempt": "1",
            "PostHog-Request-Id": str(uuid4()),
            "PostHog-Request-Timestamp": timestamp,
        })
        response = conn.getresponse()
        raw = response.read(4096)
        result = {"synthetic_event_uuid": uid,
                  "synthetic_noop_http_status": response.status,
                  "synthetic_noop_response_bounded": len(raw) <= 4096,
                  "native_synthetic_noop_acknowledged": False}
        if response.status == 200:
            try:
                body = json.loads(raw)
                result["native_synthetic_noop_acknowledged"] = (
                    body.get("results", {}).get(uid, {}).get("result") == "ok"
                )
            except (ValueError, TypeError, AttributeError):
                pass
        return result
    finally:
        conn.close()


def probe() -> dict:
    receipt = {
        "native_capture_binary_present": CAPTURE.is_file() and os.access(CAPTURE, os.X_OK),
        "local_redis_started": False,
        "native_capture_http_bound": False,
        "real_liveness_http": False,
        "invalid_capture_headers_rejected": False,
        "no_kafka_sink_enabled": True,
        "loopback_only": True,
        "real_kafka_delivery": False,
        "clickhouse_product_event_readback": False,
        "tenant_auth_end_to_end": False,
        "release_qualified": False,
    }
    if not receipt["native_capture_binary_present"] or not REDIS.is_file():
        receipt["blocker"] = "Local native Capture binary or Redis missing"
        return receipt
    if shutil.disk_usage("/tmp").free < 10 * 1024**3:
        receipt["blocker"] = "Disk reserve under 10GiB"
        return receipt
    redis_port, capture_port = unused_port(), unused_port()
    while redis_port == capture_port:
        capture_port = unused_port()
    with tempfile.TemporaryDirectory(prefix="flind-capture-native-") as folder:
        with ExitStack() as stack:
            redis_log = stack.enter_context(open(Path(folder) / "redis.log", "wb"))
            capture_log = stack.enter_context(open(Path(folder) / "capture.log", "wb"))
            rp = cp = None
            try:
                rp = subprocess.Popen(
                    [str(REDIS), "--bind", "127.0.0.1", "--port", str(redis_port),
                     "--save", "", "--appendonly", "no", "--protected-mode", "yes",
                     "--maxmemory", "32mb", "--loglevel", "warning"],
                    cwd=folder, stdin=subprocess.DEVNULL, stdout=redis_log,
                    stderr=subprocess.STDOUT,
                    env={"PATH": "/usr/bin:/bin", "HOME": folder, "LANG": "C"},
                )
                deadline = time.monotonic() + 7
                while time.monotonic() < deadline and rp.poll() is None:
                    try:
                        with socket.create_connection(("127.0.0.1", redis_port), timeout=0.3):
                            receipt["local_redis_started"] = True
                            break
                    except (OSError, TimeoutError):
                        time.sleep(0.08)
                if not receipt["local_redis_started"]:
                    receipt["blocker"] = "Temporary Redis did not bind"
                    return receipt
                env = {
                    "PATH": "/usr/bin:/bin", "HOME": folder, "LANG": "C",
                    "REDIS_URL": f"redis://127.0.0.1:{redis_port}/",
                    "KAFKA_HOSTS": "127.0.0.1:65441",
                    "ADDRESS": f"127.0.0.1:{capture_port}",
                    "CAPTURE_MODE": "events",
                    "NOOP_SINK": "true",
                    "PRINT_SINK": "false",
                    "EXPORT_PROMETHEUS": "false",
                    "GLOBAL_RATE_LIMIT_ENABLED": "false",
                    "OVERFLOW_ENABLED": "false",
                    "CAPTURE_INGESTION_WARNINGS_ENABLED": "false",
                    "OTEL_SERVICE_NAME": "flind-local-test",
                    "RUST_LOG": "warn",
                }
                cp = subprocess.Popen(
                    [str(CAPTURE)], cwd=folder, env=env, stdin=subprocess.DEVNULL,
                    stdout=capture_log, stderr=subprocess.STDOUT,
                )
                deadline = time.monotonic() + 19
                while time.monotonic() < deadline and cp.poll() is None:
                    try:
                        with socket.create_connection(("127.0.0.1", capture_port), timeout=0.3):
                            receipt["native_capture_http_bound"] = True
                            break
                    except (OSError, TimeoutError):
                        time.sleep(0.15)
                if not receipt["native_capture_http_bound"]:
                    receipt["blocker"] = "Native Capture failed to bind within 19sec"
                    return receipt
                for _ in range(8):
                    try:
                        health, _ = http("/_liveness", capture_port)
                        receipt["liveness_http_status"] = health
                        receipt["real_liveness_http"] = health == 200
                        invalid, _ = http(EXPECTED, capture_port, "POST", b'{"batch":[]}')
                        receipt["invalid_capture_http_status"] = invalid
                        receipt["invalid_capture_headers_rejected"] = 400 <= invalid < 500
                        break
                    except (OSError, TimeoutError):
                        time.sleep(0.25)
                if receipt["real_liveness_http"] and receipt["invalid_capture_headers_rejected"]:
                    receipt.update(synthetic_noop_event(capture_port))
                return receipt
            except (OSError, ValueError, subprocess.SubprocessError):
                receipt["blocker"] = "Unable to run local native Capture smoke"
                return receipt
            finally:
                terminate(cp)
                terminate(rp)
                receipt["capture_process_stopped"] = cp is None or cp.poll() is not None
                receipt["redis_process_stopped"] = rp is None or rp.poll() is not None


if __name__ == "__main__":
    result = probe()
    print(json.dumps(result, indent=2))
    success = all(result.get(key) for key in (
        "native_capture_binary_present", "local_redis_started",
        "native_capture_http_bound", "real_liveness_http",
        "invalid_capture_headers_rejected", "no_kafka_sink_enabled",
        "loopback_only", "capture_process_stopped", "redis_process_stopped",
    ))
    raise SystemExit(0 if success else 2)
