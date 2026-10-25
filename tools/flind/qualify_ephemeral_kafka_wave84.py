#!/usr/bin/env python3
"""Real ephemeral Kafka KRaft publish/consume on localhost only.

This qualifies Kafka transport only. No Flind SDK, ingestion worker or
ClickHouse materialized view is exercised. No Docker, paid services or
persistent machine Kafka configuration is used.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time


VERSION = "4.3.1"
TOPIC = "flind-wave84-events"
MIN_FREE_GIB = 10.0

EVENTS = (
    {"team_id": 101, "event": "$pageview", "distinct_id": "user-one", "properties": {"$pathname": "/home"}},
    {"team_id": 202, "event": "$pageview", "distinct_id": "user-one", "properties": {"$pathname": "/private"}},
    {"team_id": 101, "event": "purchase", "distinct_id": "user-one", "properties": {"$pathname": "/pricing"}},
)


def kafka_paths(home: Path) -> dict[str, Path]:
    if not isinstance(home, Path) or not home.is_dir():
        raise ValueError("Local Kafka distribution missing")
    result = {name: home / "bin" / ("kafka-" + name + ".sh") for name in
              ("storage", "server-start", "topics", "console-producer", "console-consumer")}
    for path in result.values():
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError("Local Kafka binary tool missing")
    if not (home / "config" / "server.properties").is_file():
        raise ValueError("Local Kafka KRaft properties missing")
    return result


def loopback_ports() -> tuple[int, int]:
    result = []
    for _ in range(2):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            result.append(listener.getsockname()[1])
    if result[0] == result[1]:
        raise ValueError("Kafka loopback port collision")
    return result[0], result[1]


def isolated_config(home: Path, private: Path, broker_port: int, controller_port: int) -> Path:
    if (
        type(broker_port) is not int or type(controller_port) is not int
        or not 1024 <= broker_port <= 65535
        or not 1024 <= controller_port <= 65535
        or broker_port == controller_port
    ):
        raise ValueError("Non-private or invalid Kafka loopback ports")
    source = (home / "config" / "server.properties").read_text(encoding="utf-8")
    changes = {
        "controller.quorum.bootstrap.servers": f"127.0.0.1:{controller_port}",
        "listeners": f"PLAINTEXT://127.0.0.1:{broker_port},CONTROLLER://127.0.0.1:{controller_port}",
        "advertised.listeners": f"PLAINTEXT://127.0.0.1:{broker_port}",
        "log.dirs": str(private / "data"),
        "auto.create.topics.enable": "false",
    }
    for key, value in changes.items():
        pattern = rf"(?m)^{re.escape(key)}=.*$"
        if re.search(pattern, source):
            if len(re.findall(pattern, source)) != 1:
                raise ValueError("Ambiguous Kafka config key")
            source = re.sub(pattern, lambda m: f"{key}={value}", source)
        elif key == "auto.create.topics.enable":
            source += "\nauto.create.topics.enable=false\n"
        else:
            raise ValueError("Required Kafka config key absent")
    conf = private / "server.properties"
    conf.write_text(source, encoding="utf-8")
    conf.chmod(0o600)
    return conf


def synthetic_messages() -> str:
    # Event payloads are constants, never derived from a user or production DB.
    assert len(EVENTS) == 3 and len({e["team_id"] for e in EVENTS}) == 2
    return "".join(json.dumps(e, separators=(",", ":"), sort_keys=True) + "\n" for e in EVENTS)


def available_disk_gib() -> float:
    return shutil.disk_usage("/tmp").free / (1024 ** 3)


def _run(command: list[str], env: dict[str, str], *, timeout: int, text_input: str | None = None):
    return subprocess.run(
        command, env=env, input=text_input, capture_output=True,
        text=True, timeout=timeout, check=False,
    )


def qualify_kafka(home: Path) -> dict:
    base = {
        "isolated_kafka_passed": False,
        "temporary_kafka_storage": True,
        "network": "127.0.0.1 only",
        "sdk_ingestion_qualified": False,
        "kafka_to_clickhouse_qualified": False,
        "dashboard_query_qualified": False,
        "release_qualified": False,
    }
    if available_disk_gib() < MIN_FREE_GIB:
        return {**base, "blocker": "At least 10 GiB of free temporary disk is required"}
    try:
        bins = kafka_paths(home)
        broker_port, controller_port = loopback_ports()
    except (OSError, ValueError):
        return {**base, "blocker": "Local Kafka 4.3 KRaft toolchain unavailable"}

    with tempfile.TemporaryDirectory(prefix="flind-kafka-") as temp:
        private = Path(temp)
        try:
            config = isolated_config(home, private, broker_port, controller_port)
        except (OSError, ValueError):
            return {**base, "blocker": "Official Kafka config incompatible with loopback-only isolation"}
        # Do not inherit arbitrary KAFKA_* environment overrides, account
        # tokens, JVM agents or a user's HOME when spawning an external tool.
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": temp,
            "TMPDIR": temp,
            "LANG": "C",
            "KAFKA_HEAP_OPTS": "-Xms256m -Xmx512m",
            "KAFKA_JVM_PERFORMANCE_OPTS": "-server -XX:+UseG1GC -XX:MaxGCPauseMillis=20",
            "JAVA_TOOL_OPTIONS": "-Djava.awt.headless=true",
            "LOG_DIR": str(private / "logs"),
        }
        if os.environ.get("JAVA_HOME"):
            env["JAVA_HOME"] = os.environ["JAVA_HOME"]
        (private / "logs").mkdir()
        server = None
        try:
            installed = _run([str(bins["topics"]), "--version"], env, timeout=18)
            if installed.returncode or not re.search(r"(?m)^4\.3\.1(?:\s|$)", installed.stdout):
                raise RuntimeError("Unsupported native Kafka distribution version")
            uid = _run([str(bins["storage"]), "random-uuid"], env, timeout=30)
            cluster_id = uid.stdout.strip()
            if uid.returncode or not re.fullmatch(r"[A-Za-z0-9_-]{22}", cluster_id):
                raise RuntimeError("Private Kafka storage identity unavailable")
            formatted = _run(
                [str(bins["storage"]), "format", "--standalone", "-t", cluster_id,
                 "-c", str(config)], env, timeout=55
            )
            if formatted.returncode:
                raise RuntimeError("Private Kafka KRaft formatting failed")

            with (private / "logs" / "server.out").open("wb") as log:
                server = subprocess.Popen(
                    [str(bins["server-start"]), str(config)], cwd=private,
                    env=env, stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            bootstrap = f"127.0.0.1:{broker_port}"
            deadline = time.monotonic() + 55
            ready = False
            while time.monotonic() < deadline:
                if server.poll() is not None or available_disk_gib() < MIN_FREE_GIB:
                    break
                try:
                    probe = _run([str(bins["topics"]), "--bootstrap-server", bootstrap, "--list"], env, timeout=8)
                    if probe.returncode == 0:
                        ready = True
                        break
                except subprocess.TimeoutExpired:
                    pass
                time.sleep(1)
            if not ready:
                raise RuntimeError("Private Kafka broker readiness unavailable")

            topic = _run(
                [str(bins["topics"]), "--bootstrap-server", bootstrap,
                 "--create", "--topic", TOPIC, "--partitions", "1", "--replication-factor", "1"],
                env, timeout=24,
            )
            if topic.returncode:
                raise RuntimeError("Private synthetic Kafka topic could not be created")

            sent = _run(
                [str(bins["console-producer"]), "--bootstrap-server", bootstrap,
                 "--topic", TOPIC, "--producer-property", "acks=all"],
                env, timeout=30, text_input=synthetic_messages(),
            )
            if sent.returncode:
                raise RuntimeError("Synthetic Kafka producer unsuccessful")
            received = _run(
                [str(bins["console-consumer"]), "--bootstrap-server", bootstrap,
                 "--topic", TOPIC, "--from-beginning",
                 "--max-messages", str(len(EVENTS)), "--timeout-ms", "13000"],
                env, timeout=35,
            )
            if received.returncode:
                raise RuntimeError("Synthetic Kafka consumer unsuccessful")
            records = [json.loads(line) for line in received.stdout.splitlines() if line.strip()]
            if records != list(EVENTS):
                raise ValueError("Kafka messages differ from the exact synthetic event payloads")
            return {
                **base,
                "isolated_kafka_passed": True,
                "kafka_version": VERSION,
                "synthetic_events_published": len(EVENTS),
                "synthetic_events_consumed": len(records),
                "exact_json_message_roundtrip": True,
                "two_teams_with_colliding_distinct_ids": True,
                "temporary_topic": True,
            }
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
            return {**base, "blocker": "Bounded real Kafka publish/consume qualification failed"}
        finally:
            if server is not None and server.poll() is None:
                try:
                    os.killpg(server.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    server.wait(timeout=9)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(server.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    server.wait(timeout=6)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kafka-home", type=Path, required=True,
                        help="Locally extracted official Apache Kafka 4.3.1 distribution; no auto-download")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    receipt = qualify_kafka(args.kafka_home)
    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print("Private Kafka transport:", "PASS" if receipt["isolated_kafka_passed"] else "BLOCKED")
        print("Flind SDK -> Kafka -> ClickHouse -> dashboard: NOT QUALIFIED")
    return 0 if receipt["isolated_kafka_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
