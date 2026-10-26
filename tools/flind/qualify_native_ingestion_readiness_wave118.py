#!/usr/bin/env python3
"""Real native Rust ingestion-consumer worker-readiness qualification.

NO production Kafka, Node gRPC worker or persistent data. Real Rust process,
a strictly synthetic localhost HTTP worker probe, and real liveness/readiness
queries. Does not qualify Kafka connectivity or production readiness.
"""
from __future__ import annotations

from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from threading import Thread
import time

BINARY = Path(os.environ.get("FLIND_INGESTION_CONSUMER_BINARY")
              or "/tmp/flind-wave110-rust-target/debug/ingestion-consumer")


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def terminate_owned(child: subprocess.Popen | None) -> bool:
    if child is None:
        return True
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=4)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=4)
    return child.poll() is not None


def probe_worker(available: bool) -> dict:
    result = {
        "native_binary_exists": BINARY.is_file(),
        "real_native_health_server_bound": False,
        "liveness_always_200": False,
        "unverified_worker_not_ready": False,
        "verified_worker_eventually_ready": False,
        "native_consumer_child_stopped": False,
        "fake_worker_server_stopped": False,
        "kafka_connectivity_qualified": False,
        "real_node_grpc_worker_qualified": False,
        "real_product_event_ingestion_qualified": False,
        "release_qualified": False,
    }
    if not BINARY.is_file() or shutil.disk_usage("/tmp").free < 10 * 1024**3:
        result["blocker"] = "Native Rust binary or free disk unavailable"
        return result

    class Worker(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/_ready":
                self.send_error(404)
                return
            status = 200 if available else 503
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            return

    fake_worker = ThreadingHTTPServer(("127.0.0.1", 0), Worker)
    fake_worker.daemon_threads = True
    worker = Thread(target=fake_worker.serve_forever, daemon=True)
    worker.start()
    consumer_port = unused_port()
    while consumer_port == fake_worker.server_port:
        consumer_port = unused_port()

    def health(name: str) -> int:
        connection = HTTPConnection("127.0.0.1", consumer_port, timeout=1)
        try:
            connection.request("GET", name)
            response = connection.getresponse()
            response.read(256)
            return response.status
        finally:
            connection.close()

    try:
        with tempfile.TemporaryDirectory(prefix="flind-wave118-ready-") as directory:
            env = {
                "PATH": "/usr/bin:/bin", "HOME": directory, "LANG": "C",
                "RUST_LOG": "warn",
                "KAFKA_HOSTS": "127.0.0.1:65441",
                "KAFKA_CONSUMER_METADATA_BROKER_LIST": "127.0.0.1:65441",
                "INGESTION_CONSUMER_CONSUME_TOPIC": "flind-wave118-test-not-production",
                "WORKER_DISCOVERY_MODE": "static",
                "WORKER_ADDRESSES": f"http://127.0.0.1:{fake_worker.server_port}",
                "BIND_HOST": "127.0.0.1",
                "BIND_PORT": str(consumer_port),
                "EXPORT_PROMETHEUS": "false",
            }
            child = None
            try:
                with open(Path(directory) / "consumer.log", "wb") as output:
                    child = subprocess.Popen(
                        [str(BINARY)], cwd=directory, env=env,
                        stdin=subprocess.DEVNULL,
                        stdout=output, stderr=subprocess.STDOUT,
                    )
                    statuses: list[tuple[int, int]] = []
                    limit = time.monotonic() + (12 if available else 7)
                    while time.monotonic() < limit and child.poll() is None:
                        try:
                            statuses.append((health("/_liveness"), health("/_readiness")))
                        except OSError:
                            pass
                        if available and any(x[1] == 200 for x in statuses) and len(statuses) >= 4:
                            break
                        time.sleep(0.45)
                    result["real_native_health_server_bound"] = len(statuses) >= 3
                    result["liveness_always_200"] = bool(statuses) and all(x[0] == 200 for x in statuses)
                    result["unverified_worker_not_ready"] = bool(statuses) and all(
                        x[1] == 503 for x in statuses
                    ) if not available else False
                    result["verified_worker_eventually_ready"] = bool(statuses) and any(
                        x[1] == 200 for x in statuses
                    ) if available else False
                    result["sample_count"] = len(statuses)
                    result["observed_readiness_codes"] = sorted(set(x[1] for x in statuses))
            except (OSError, subprocess.SubprocessError):
                result["blocker"] = "Native Rust consumer failed to start"
            finally:
                result["native_consumer_child_stopped"] = terminate_owned(child)
    finally:
        fake_worker.shutdown()
        fake_worker.server_close()
        worker.join(timeout=3)
        result["fake_worker_server_stopped"] = not worker.is_alive()

    return result


def qualify() -> dict:
    absent = probe_worker(False)
    verified = probe_worker(True)
    passed = (
        absent["real_native_health_server_bound"]
        and absent["liveness_always_200"]
        and absent["unverified_worker_not_ready"]
        and absent["native_consumer_child_stopped"]
        and absent["fake_worker_server_stopped"]
        and verified["real_native_health_server_bound"]
        and verified["liveness_always_200"]
        and verified["verified_worker_eventually_ready"]
        and verified["native_consumer_child_stopped"]
        and verified["fake_worker_server_stopped"]
    )
    return {
        "native_consumer_verified_worker_readiness_qualified": passed,
        "no_worker_receipt": absent,
        "synthetic_healthy_worker_receipt": verified,
        "real_kafka_connectivity_qualified": False,
        "node_worker_grpc_pipeline_qualified": False,
        "durable_product_ingestion_qualified": False,
        "release_qualified": False,
    }


if __name__ == "__main__":
    result = qualify()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["native_consumer_verified_worker_readiness_qualified"] else 2)
