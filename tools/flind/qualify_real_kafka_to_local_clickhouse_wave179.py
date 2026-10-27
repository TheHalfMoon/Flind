#!/usr/bin/env python3
"""Real isolated Kafka 4.3.1 -> bounded Python relay -> ClickHouse local smoke.

Uses fixed synthetic Flind records and verified first-party events_recent HCL.
No SDK, Rust worker, materialized view, user authorization or release claims.
Kafka data and ClickHouse state live only in marked disposable scratch folders.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
import hashlib
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
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_ephemeral_kafka_wave84 import (
    EVENTS, isolated_config, kafka_paths, loopback_ports,
)
from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import (
    EXPECTED_COLUMNS, FIELDS, checked_scratch, scoped_sql, verified_schema,
)
from tools.flind.qualify_local_clickhouse_insert_wave178 import insert_sql

KAFKA_VERSION = "4.3.1"
MARKER = ".flind-clickhouse-local-v1"
MARKER_CONTENT = "FLIND_CLICKHOUSE_LOCAL_SCRATCH_V1\n"
MIN_FREE_GIB = 3.0
MAX_USED_MB = 500
MAX_EVENT_BYTES = 2048
TOPIC = "flind_wave179_synthetic_only"
QUEUE_GROUP = "flind-wave179-scratch-group"
SAFE_BROKER = re.compile(r"127\.0\.0\.1:[0-9]{4,5}\Z")


class Refusal(Exception):
    pass


def admitted(kafka_home: Path, repo: Path, scratch: Path, clickhouse: str) -> None:
    checked_scratch(repo, scratch, "HEAD")
    boundary = Path("/private/tmp").resolve()
    if (kafka_home.is_symlink() or not kafka_home.is_dir()
            or boundary not in kafka_home.resolve().parents):
        raise Refusal("unapproved_kafka_distribution")
    kafka_paths(kafka_home)
    exe = Path(clickhouse)
    if not exe.is_file() or not os.access(exe, os.X_OK):
        raise Refusal("unavailable_local_clickhouse")
    if shutil.disk_usage(scratch).free < MIN_FREE_GIB * (1024 ** 3):
        raise Refusal("insufficient_local_scratch_disk_reserve")


def broker_environment(scratch: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(scratch),
        "TMPDIR": str(scratch),
        "LANG": "C",
        "KAFKA_HEAP_OPTS": "-Xms128m -Xmx384m",
        "KAFKA_JVM_PERFORMANCE_OPTS": "-server -XX:+UseG1GC -XX:MaxGCPauseMillis=20",
        "JAVA_TOOL_OPTIONS": "-Djava.awt.headless=true",
        "LOG_DIR": str(scratch / "logs"),
        **({"JAVA_HOME": os.environ["JAVA_HOME"]} if os.environ.get("JAVA_HOME") else {}),
    }


def bounded_tool(command: list[str], env: dict[str, str], timeout: int = 35) -> str:
    try:
        done = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True,
            check=False, text=True, env=env, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refusal("local_kafka_tool_unavailable") from exc
    if done.returncode or len(done.stdout) > 100_000:
        raise Refusal("local_kafka_command_failed")
    return done.stdout.strip()


def fixed_payloads() -> tuple[bytes, ...]:
    if len(EVENTS) != 3 or {event["team_id"] for event in EVENTS} != {101, 202}:
        raise Refusal("unrecognized_synthetic_kafka_fixture")
    return tuple(json.dumps(row, sort_keys=True, separators=(",", ":")).encode("ascii")
                 for row in EVENTS)


def readback_accepted(records: list[dict]) -> bool:
    return (
        type(records) is list
        and len(records) == len(EVENTS)
        and all(type(row) is dict and row == expected for row, expected in zip(records, EVENTS))
    )


def produce_consume(bootstrap: str, payloads: tuple[bytes, ...]) -> list[dict]:
    if not SAFE_BROKER.fullmatch(bootstrap) or len(payloads) != 3:
        raise Refusal("unsafe_kafka_destination_or_fixture")
    from confluent_kafka import Consumer, Producer
    producer = Producer({
        "bootstrap.servers": bootstrap, "acks": "all", "message.timeout.ms": 10000,
        "socket.timeout.ms": 5000, "client.id": "flind-wave179-synthetic-publisher",
    })
    errors: list[str] = []

    def delivered(err, _msg):
        if err:
            errors.append(type(err).__name__)

    for payload in payloads:
        if len(payload) > MAX_EVENT_BYTES:
            raise Refusal("oversized_synthetic_kafka_record")
        producer.produce(TOPIC, value=payload, on_delivery=delivered)
    remaining = producer.flush(16)
    if remaining or errors:
        raise Refusal("real_kafka_delivery_ack_failed")
    consumer = Consumer({
        "bootstrap.servers": bootstrap,
        "group.id": QUEUE_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "session.timeout.ms": 7000,
        "client.id": "flind-wave179-synthetic-consumer",
    })
    try:
        consumer.subscribe([TOPIC])
        records: list[dict] = []
        end = time.monotonic() + 22
        while time.monotonic() < end and len(records) < len(payloads):
            message = consumer.poll(0.7)
            if message is None:
                continue
            if message.error():
                raise Refusal("real_kafka_consumer_error")
            raw = message.value()
            if not isinstance(raw, bytes) or len(raw) > MAX_EVENT_BYTES:
                raise Refusal("unexpected_kafka_record_length")
            records.append(json.loads(raw))
        if not readback_accepted(records):
            raise Refusal("kafka_records_not_exact_synthetic_fixture")
        consumer.commit(asynchronous=False)
        return records
    finally:
        consumer.close()


def clickhouse_relay(scratch: Path, records: list[dict], schema: dict[str, str],
                     executable: str) -> dict[str, object]:
    if not readback_accepted(records) or schema != EXPECTED_COLUMNS:
        raise Refusal("untrusted_kafka_record_or_flind_schema")
    events: list[dict[str, object]] = []
    for index, item in enumerate(records):
        events.append({
            "uuid": str(UUID(int=17901 + index)),
            "event": item["event"],
            "properties": json.dumps(item["properties"], separators=(",", ":"), sort_keys=True),
            "timestamp": f"2026-10-27 12:00:0{index}.000000",
            "team_id": item["team_id"],
            "distinct_id": item["distinct_id"],
        })
    ddl = ", ".join(f"{name} {schema[name]}" for name in FIELDS)
    queries = [
        f"CREATE TABLE events ({ddl}) ENGINE = Memory",
        insert_sql(events, schema),
        scoped_sql(101, kind="counts"),
        scoped_sql(202, kind="counts"),
        scoped_sql(101, kind="events"),
        scoped_sql(202, kind="events"),
        scoped_sql(303, kind="counts"),
    ]
    folder = scratch / "wave179-local-engine"
    stdout = scratch / "wave179-clickhouse-results.jsonl"
    stderr = scratch / "wave179-clickhouse-errors.log"
    if any(path.exists() or path.is_symlink() for path in (folder, stdout, stderr)):
        raise Refusal("clickhouse_scratch_session_exists")
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            process = subprocess.run(
                [executable, "local", "--multiquery", "--path", str(folder),
                 "--max_memory_usage=134217728", "--query", ";\n".join(queries) + ";\n"],
                cwd=scratch, stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, check=False, timeout=24,
                env={**os.environ, "HOME": str(scratch)},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Refusal("local_clickhouse_relay_timeout") from exc
    if process.returncode or stdout.stat().st_size > 40_000:
        raise Refusal("local_clickhouse_insert_or_query_failed")
    try:
        lines = [json.loads(row) for row in stdout.read_text().splitlines() if row]
    except (ValueError, UnicodeError) as exc:
        raise Refusal("invalid_clickhouse_relay_result") from exc
    counts = [r for r in lines if "event_count" in r]
    evs = [r for r in lines if "event" in r]
    if counts != [{"team_id": 101, "event_count": 2}, {"team_id": 202, "event_count": 1}]:
        raise Refusal("cross_team_kafka_relay_aggregate_mismatch")
    if (len(evs) != 3 or {r["team_id"] for r in evs} != {101, 202}
            or sum(r["team_id"] == 101 for r in evs) != 2
            or sum(r["team_id"] == 202 for r in evs) != 1):
        raise Refusal("kafka_relay_row_invariant_failed")
    return {"synthetic_rows_inserted": 3, "clickhouse_sql_statements": len(queries),
            "team_101_rows": 2, "team_202_rows": 1, "nonexistent_team_303_rows": 0}


def qualify(repo: Path, kafka_home: Path, scratch: Path, *,
            clickhouse: str = "/opt/homebrew/bin/clickhouse",
            on_broker_ready: Callable[[str, Path], dict[str, object]] | None = None
            ) -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "real-local-kafka-to-clickhouse-memory-synthetic-relay",
        "kafka_431_broker_qualified": False,
        "real_kafka_producer_ack_qualified": False,
        "real_kafka_consumer_qualified": False,
        "local_clickhouse_relay_qualified": False,
        "first_party_rust_capture_qualified": False,
        "first_party_kafka_ingester_qualified": False,
        "persistent_clickhouse_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "flind_sdk_to_dashboard_qualified": False,
        "release_qualified": False,
    }
    started = time.monotonic()
    server: subprocess.Popen | None = None
    private: Path | None = None
    try:
        admitted(kafka_home, repo, scratch, clickhouse)
        commit, schema = verified_schema(repo, "HEAD")
        report["source_commit"] = commit
        binaries = kafka_paths(kafka_home)
        broker, controller = loopback_ports()
        if broker == controller:
            raise Refusal("loopback_ports_not_unique")
        private = Path(tempfile.mkdtemp(prefix="flind-wave179-kafka-", dir=scratch))
        (private / ".flind-wave179-owned").write_text("FLIND_WAVE179_SCRATCH_V1\n")
        config = isolated_config(kafka_home, private, broker, controller)
        (private / "logs").mkdir()
        env = broker_environment(private)
        version = bounded_tool([str(binaries["topics"]), "--version"], env, timeout=20)
        if not re.match(r"^4\.3\.1(?:\s|$)", version):
            raise Refusal("unexpected_cached_kafka_version")
        cluster = bounded_tool([str(binaries["storage"]), "random-uuid"], env, timeout=25)
        if not re.fullmatch(r"[A-Za-z0-9_-]{22}", cluster):
            raise Refusal("invalid_synthetic_kafka_cluster_id")
        bounded_tool(
            [str(binaries["storage"]), "format", "--standalone", "-t", cluster,
             "-c", str(config)], env, timeout=40,
        )
        log = private / "logs" / "server.out"
        with log.open("wb") as stream:
            server = subprocess.Popen(
                [str(binaries["server-start"]), str(config)],
                cwd=private, env=env, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
            )
        bootstrap = f"127.0.0.1:{broker}"
        ready = False
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            if server.poll() is not None:
                break
            if shutil.disk_usage(scratch).free < MIN_FREE_GIB * 1024**3:
                raise Refusal("kafka_disk_reserve_dropped")
            total_size = sum(p.stat().st_size for p in private.rglob("*") if p.is_file())
            if total_size > MAX_USED_MB * 1024**2:
                raise Refusal("scratch_kafka_resource_budget_exceeded")
            try:
                bounded_tool([str(binaries["topics"]), "--bootstrap-server", bootstrap,
                              "--list"], env, timeout=7)
                ready = True
                break
            except Refusal:
                time.sleep(0.8)
        if not ready:
            raise Refusal("real_kafka_broker_not_ready")
        report["kafka_431_broker_qualified"] = True
        bounded_tool(
            [str(binaries["topics"]), "--bootstrap-server", bootstrap,
             "--create", "--topic", TOPIC,
             "--partitions", "1", "--replication-factor", "1"], env, timeout=25,
        )
        records = produce_consume(bootstrap, fixed_payloads())
        report["real_kafka_producer_ack_qualified"] = True
        report["real_kafka_consumer_qualified"] = True
        report.update(clickhouse_relay(scratch, records, schema, clickhouse))
        report["local_clickhouse_relay_qualified"] = True
        report["synthetic_kafka_event_count"] = len(records)
        report["kafka_version"] = KAFKA_VERSION
        # Optional extension may inspect this one owned Kafka instance;
        # never promote a synthetic callback into product/release status.
        if on_broker_ready is not None:
            native = on_broker_ready(bootstrap, private)
            if not isinstance(native, dict):
                raise Refusal("invalid_private_kafka_extension_receipt")
            report["optional_private_kafka_probe"] = native
    except (Refusal, ValueError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        report["blocker"] = str(exc) if isinstance(exc, Refusal) else type(exc).__name__
    finally:
        if server is not None:
            if server.poll() is None:
                try:
                    os.killpg(server.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    server.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(server.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    server.wait(timeout=6)
            report["owned_kafka_process_stopped"] = server.poll() is not None
        else:
            report["owned_kafka_process_stopped"] = True
        # Delete only the unique, marker-verified private child we created.
        report["owned_kafka_scratch_removed"] = private is None
        if private is not None:
            try:
                if (not private.is_symlink() and private.parent.resolve() == scratch.resolve()
                        and (private / ".flind-wave179-owned").read_text()
                        == "FLIND_WAVE179_SCRATCH_V1\n"
                        and report["owned_kafka_process_stopped"]):
                    shutil.rmtree(private)
                    report["owned_kafka_scratch_removed"] = not private.exists()
                else:
                    report.setdefault("blocker", "owned_kafka_cleanup_scope_refused")
            except (OSError, UnicodeError):
                report.setdefault("blocker", "owned_kafka_cleanup_failed")
        report["elapsed_seconds"] = round(time.monotonic() - started, 1)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--kafka-home", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--clickhouse", default="/opt/homebrew/bin/clickhouse")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = qualify(args.repo, args.kafka_home, args.scratch, clickhouse=args.clickhouse)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Flind real private Kafka -> ClickHouse local relay:",
              "PASS" if result["local_clickhouse_relay_qualified"] else "BLOCKED")
    return 0 if (
        "blocker" not in result and result["local_clickhouse_relay_qualified"]
        and result["owned_kafka_process_stopped"]
        and result["owned_kafka_scratch_removed"]
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
