#!/usr/bin/env python3
"""Wave119: real Rust ingestion consumer joins real isolated Kafka 4.3.1 group.

The broker and consumer are real. Worker is an explicitly synthetic *HTTP
readiness-only* service, no Node gRPC, no Kafka events on the test topic.
This does not prove event processing/commits or full product readiness.
"""
from __future__ import annotations

from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Thread
import time

from tools.flind.qualify_ephemeral_kafka_wave84 import qualify_kafka
from tools.flind.qualify_native_capture_server_wave111 import unused_port, terminate
from tools.flind.qualify_native_capture_kafka_wave113 import DEFAULT_HOME, kafka_cli_env, run_cli

CONSUMER = Path(os.environ.get("FLIND_INGESTION_CONSUMER_BINARY")
                or "/tmp/flind-wave110-rust-target/debug/ingestion-consumer")
GROUP = "flind-wave119-native-consumer"
TOPIC = "flind-wave119-empty-native-consumer"
MIN_GIB = 10


def within_broker(bootstrap: str) -> dict:
    receipt = {
        "real_native_consumer_executable": CONSUMER.is_file(),
        "real_kafka_431_group_join": False,
        "real_native_health_bound": False,
        "native_readiness_worker_gate": False,
        "owned_native_consumer_stopped": False,
        "owned_fake_worker_stopped": False,
        "production_node_grpc_worker_executed": False,
        "events_processed_with_real_worker": False,
        "kafka_offsets_committed_after_ack": False,
        "production_clickhouse_schema_qualified": False,
        "release_qualified": False,
    }
    if not CONSUMER.is_file() or shutil.disk_usage("/tmp").free < MIN_GIB * 1024**3:
        return {**receipt, "blocker": "Native consumer or minimum disk reserve unavailable"}
    if not bootstrap.startswith("127.0.0.1:"):
        return {**receipt, "blocker": "Kafka broker not localhost"}
    kafka_home = DEFAULT_HOME
    topic_cli = kafka_home / "bin/kafka-topics.sh"
    groups_cli = kafka_home / "bin/kafka-consumer-groups.sh"
    if not topic_cli.is_file() or not groups_cli.is_file():
        return {**receipt, "blocker": "Apache Kafka4.3.1 CLI tools missing"}

    class Worker(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/_ready":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            return

    worker_server = ThreadingHTTPServer(("127.0.0.1", 0), Worker)
    worker_server.daemon_threads = True
    worker_thread = Thread(target=worker_server.serve_forever, daemon=True)
    worker_thread.start()
    consumer_port = unused_port()
    while consumer_port == worker_server.server_port:
        consumer_port = unused_port()
    consumer = None
    try:
        with tempfile.TemporaryDirectory(prefix="flind-wave119-native-") as temp:
            cli_env = kafka_cli_env(temp)
            created = run_cli([
                str(topic_cli), "--bootstrap-server", bootstrap,
                "--create", "--topic", TOPIC,
                "--partitions", "1", "--replication-factor", "1",
            ], cli_env, timeout=23)
            if created.returncode:
                return {**receipt, "blocker": "Private consumer topic creation failed"}
            env = {
                "PATH": "/usr/bin:/bin", "HOME": temp, "LANG": "C",
                "KAFKA_HOSTS": bootstrap,
                "KAFKA_CONSUMER_METADATA_BROKER_LIST": bootstrap,
                "KAFKA_CONSUMER_GROUP_ID": GROUP,
                "INGESTION_CONSUMER_GROUP_ID": GROUP,
                "INGESTION_CONSUMER_CONSUME_TOPIC": TOPIC,
                "KAFKA_CONSUMER_AUTO_OFFSET_RESET": "earliest",
                "WORKER_DISCOVERY_MODE": "static",
                "WORKER_ADDRESSES": f"http://127.0.0.1:{worker_server.server_port}",
                "BIND_HOST": "127.0.0.1",
                "BIND_PORT": str(consumer_port),
                "EXPORT_PROMETHEUS": "false",
                "RUST_LOG": "warn",
                # Never connect to production gRPC/worker; no topic events
                # are published to the native consumer's separate topic.
                "INGESTION_WORKER_GRPC_PORT": "65442",
                "CONSUMER_BATCH_SIZE": "1",
                "CONSUMER_BATCH_TIMEOUT_MS": "200",
            }
            with open(Path(temp) / "consumer.out", "wb") as log:
                consumer = subprocess.Popen(
                    [str(CONSUMER)], cwd=temp, env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT,
                )
                deadline = time.monotonic() + 32
                statuses: set[int] = set()
                while time.monotonic() < deadline and consumer.poll() is None:
                    try:
                        connection = HTTPConnection("127.0.0.1", consumer_port, timeout=1)
                        try:
                            connection.request("GET", "/_readiness")
                            response = connection.getresponse()
                            statuses.add(response.status)
                            response.read(128)
                        finally:
                            connection.close()
                    except OSError:
                        pass
                    try:
                        group = run_cli([
                            str(groups_cli), "--bootstrap-server", bootstrap,
                            "--describe", "--group", GROUP, "--state",
                        ], cli_env, timeout=12)
                        if group.returncode == 0:
                            for row in group.stdout.splitlines():
                                cols = row.split()
                                if (
                                    cols and cols[0] == GROUP
                                    and "Stable" in cols
                                    and cols[-1] == "1"
                                ):
                                    receipt["real_kafka_431_group_join"] = True
                                    break
                    except subprocess.TimeoutExpired:
                        pass
                    if receipt["real_kafka_431_group_join"] and 200 in statuses:
                        break
                    time.sleep(0.4)
                receipt["native_readiness_worker_gate"] = 200 in statuses
                receipt["real_native_health_bound"] = bool(statuses)
                receipt["readiness_codes_observed"] = sorted(statuses)
                if not receipt["real_kafka_431_group_join"]:
                    receipt["blocker"] = "Native Kafka consumer group member not confirmed"
                    # Controlled, private child environment only; include bounded
                    # startup diagnostics but never dump inherited credentials.
                    log.flush()
                    lines = (Path(temp) / "consumer.out").read_text(errors="replace").splitlines()
                    receipt["local_native_startup_diagnostic"] = [line[:230] for line in lines[-6:]]
                    receipt["native_consumer_exit_code"] = consumer.poll()
    finally:
        terminate(consumer)
        receipt["owned_native_consumer_stopped"] = consumer is None or consumer.poll() is not None
        worker_server.shutdown()
        worker_server.server_close()
        worker_thread.join(timeout=4)
        receipt["owned_fake_worker_stopped"] = not worker_thread.is_alive()
    return receipt


def qualify() -> dict:
    broker = qualify_kafka(DEFAULT_HOME, on_broker_ready=within_broker)
    native = broker.get("native_capture_relay") or {}
    passed = bool(
        broker.get("isolated_kafka_passed") is True
        and native.get("real_kafka_431_group_join") is True
        and native.get("owned_native_consumer_stopped") is True
        and native.get("owned_fake_worker_stopped") is True
        and native.get("native_readiness_worker_gate") is True
    )
    return {
        "actual_native_rust_consumer_kafka_group_qualified": passed,
        "isolated_kafka_431_passed": broker.get("isolated_kafka_passed") is True,
        "native_receipt": native,
        "node_grpc_worker_qualified": False,
        "kafka_event_processing_qualified": False,
        "kafka_ack_offset_commit_qualified": False,
        "clickhouse_product_schema_qualified": False,
        "release_qualified": False,
        **({"blocker": native.get("blocker") or broker.get("blocker") or
            "Native Kafka group not qualified"} if not passed else {}),
    }


if __name__ == "__main__":
    receipt = qualify()
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["actual_native_rust_consumer_kafka_group_qualified"] else 2)
