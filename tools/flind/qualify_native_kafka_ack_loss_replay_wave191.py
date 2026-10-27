#!/usr/bin/env python3
"""Wave191: kill test Node AFTER durable ClickHouse readback, BEFORE gRPC ACK.

Then confirm native Rust rdkafka did not commit; restart test Node against
the same persisted MergeTree; redeliver Kafka, ACK and commit only after
rechecking all three UUIDs. The Node StreamIngestDriver is a TEST DOUBLE,
not Flind's production pipeline. No exactly-once/release qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind import qualify_native_rust_kafka_node_mergetree_wave190 as base
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import (
    qualify as kafka_qualify, TOPIC,
)
from tools.flind.qualify_real_kafka_durable_mergetree_wave189 import attested_supported_runtime

OWNER = ".flind-wave191-owner"
OWNER_VALUE = "FLIND_WAVE191_ACK_LOSS_REPLAY_V1\n"
PINNED_FIXTURE_GIT_SHA1 = "5d688ed7e7df4a21dabe15982b926373ae1502bf"
GROUP = "flind-wave190-native-rdkafka-durable"
EXPECTED_ROWS = [
    {"uuid": "00000000-0000-4000-8000-000000019001", "team_id": 101, "event": "$pageview"},
    {"uuid": "00000000-0000-4000-8000-000000019002", "team_id": 202, "event": "$pageview"},
    {"uuid": "00000000-0000-4000-8000-000000019003", "team_id": 101, "event": "purchase"},
]


class Rejected(ValueError):
    pass


def derived_fixture(original: bytes, *, crash: bool) -> bytes:
    oid = hashlib.sha1(f"blob {len(original)}\0".encode() + original).hexdigest()
    if oid != PINNED_FIXTURE_GIT_SHA1:
        raise Rejected("wave190_original_node_fixture_source_changed")
    text = original.decode("utf-8")
    marker = "    verified=true\n    const ack="
    if text.count(marker) != 1:
        raise Rejected("original_node_durable_ack_boundary_missing")
    if crash:
        text = text.replace(
            marker,
            "    verified=true\n"
            "    // Test-only hard crash AFTER the second ClickHouse process readback\n"
            "    // but BEFORE the original gRPC WorkerIngestServer is allowed to ACK.\n"
            "    process.exit(73)\n"
            "    const ack=",
        )
    else:
        begin = text.find("    const start=sql(")
        end = text.find("    if(start.length!==0)", begin)
        if begin < 0 or end <= begin:
            raise Rejected("original_node_replay_insert_boundary_missing")
        # Test-only recovery driver: assert the already persisted rows and ACK
        # without inserting a second time. NOT product deduplication logic.
        text = text[:begin] + "    const start=[]\n" + text[end:]
    return text.encode("utf-8")


def node_fixture_install(original: bytes, *, crash: bool) -> None:
    target = base.NODE / "server-kafka-durable-wire.mjs"
    if target.is_symlink() or not target.is_file():
        raise Rejected("unsafe_test_node_fixture_path")
    target.write_bytes(derived_fixture(original, crash=crash))
    builder = subprocess.run(
        ["node", "build-kafka-durable-wire.mjs"], cwd=base.NODE,
        stdin=subprocess.DEVNULL, capture_output=True, timeout=15, check=False,
    )
    if (builder.returncode or len(builder.stdout) > 1200
            or b"FLIND_WAVE190_ORIGINAL_NODE_SERVER_BUNDLE_PASS" not in builder.stdout):
        raise Rejected("wave191_node_test_bundle_failed")


def disk_rows(binary: Path, scratch: Path) -> list[dict]:
    session = scratch / "wave190-mergetree-durable"
    if session.is_symlink() or not session.is_dir():
        raise Rejected("durable_disk_state_missing")
    result = subprocess.run(
        [str(binary), "local", "--path", str(session), "--max_memory_usage=134217728",
         "--max_threads=2", "--query",
         "SELECT uuid,team_id,event FROM events ORDER BY uuid FORMAT JSONEachRow"],
        cwd=scratch, capture_output=True, stdin=subprocess.DEVNULL,
        timeout=24, check=False, env={**os.environ, "HOME": str(scratch)},
    )
    if result.returncode or len(result.stdout) > 12000 or len(result.stderr) > 4000:
        raise Rejected("clickhouse_post_crash_reopen_failed")
    try:
        rows = [json.loads(line) for line in result.stdout.splitlines() if line]
    except (ValueError, UnicodeError) as exc:
        raise Rejected("clickhouse_post_crash_invalid_json") from exc
    if rows != EXPECTED_ROWS:
        raise Rejected("crash_replay_durable_uuid_team_event_mismatch")
    if not any(p.name == "checksums.txt" for p in (session / "store").rglob("checksums.txt")):
        raise Rejected("durable_mergetree_part_missing")
    return rows


def kafka_committed(bootstrap: str) -> int:
    from confluent_kafka import Consumer, TopicPartition
    consumer = Consumer({
        "bootstrap.servers": bootstrap, "group.id": GROUP,
        "enable.auto.commit": False, "auto.offset.reset": "earliest",
        "client.id": "flind-wave191-offset-audit",
    })
    try:
        parts = consumer.committed([TopicPartition(TOPIC, 0)], timeout=9)
        if len(parts) != 1 or parts[0].topic != TOPIC or parts[0].partition != 0:
            raise Rejected("unexpected_native_kafka_offset_audit")
        return parts[0].offset
    finally:
        consumer.close()


def native_once(bootstrap: str, binary: Path, scratch: Path, *,
                crash: bool) -> dict[str, object]:
    node = None
    result: dict[str, object] = {}
    try:
        node = subprocess.Popen(
            ["node", "dist/server-kafka-durable-wire.mjs"], cwd=base.NODE,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, start_new_session=True,
            env={**os.environ, "NODE_OPTIONS": "",
                 "FLIND_WAVE190_CLICKHOUSE_BIN": str(binary),
                 "FLIND_WAVE190_CLICKHOUSE_STATE": str(scratch / "wave190-mergetree-durable")},
        )
        if not node.stdout:
            raise Rejected("test_node_stream_unavailable")
        ready, _, _ = select.select([node.stdout], [], [], 9)
        if not ready:
            raise Rejected("test_node_grpc_start_deadline")
        raw = node.stdout.readline()
        if len(raw) > 600:
            raise Rejected("oversized_node_listener")
        line = json.loads(raw)
        port = line.get("port")
        if type(port) is not int or not 1024 <= port <= 65535:
            raise Rejected("invalid_test_node_listener")
        native = subprocess.run(
            [str(base.RUST)], cwd=base.RUST.parent,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=57,
            env={**os.environ, "FLIND_WAVE190_BROKER": bootstrap,
                 "FLIND_WAVE190_PORT": str(port)},
        )
        result["native_exit_code"] = native.returncode
        if crash:
            if native.returncode == 0:
                raise Rejected("rust_succeeded_without_durable_node_ack")
        else:
            if native.returncode or len(native.stdout) > 3000:
                raise Rejected("rust_replay_grpc_or_commit_failed")
            try:
                parsed = json.loads(native.stdout)
            except (ValueError, UnicodeError) as exc:
                raise Rejected("invalid_original_rust_commit_receipt") from exc
            if not base.approved_native_receipt(parsed):
                raise Rejected("original_rust_replay_ack_or_commit_invalid")
            result["valid_original_rust_commit_receipt"] = True
    finally:
        if node is not None:
            if crash:
                try:
                    node.wait(timeout=9)
                except subprocess.TimeoutExpired:
                    raise Rejected("test_node_did_not_crash_before_ack")
            else:
                if node.poll() is None:
                    try:
                        os.killpg(node.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                try:
                    node.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(node.pid, signal.SIGKILL)
                    node.wait(timeout=5)
            result["node_exit_code"] = node.returncode
            if node.stdout:
                rest = node.stdout.read(1400)
                if not crash:
                    try:
                        result["stop_receipt"] = json.loads(rest.strip())
                    except (ValueError, UnicodeError):
                        result["stop_receipt"] = {}
                node.stdout.close()
            if node.stderr:
                node.stderr.close()
    if crash and result.get("node_exit_code") != 73:
        raise Rejected("expected_hard_node_crash_code_not_observed")
    if not crash and not base.approved_node_stop(
        result.get("stop_receipt", {}), result.get("node_exit_code")
    ):
        raise Rejected("original_node_recovery_stop_receipt_invalid")
    return result


def test_broker(bootstrap: str, binary: Path, scratch: Path,
                original_node: bytes) -> dict[str, object]:
    receipt: dict[str, object] = {
        "actual_ack_loss_replay_qualified": False,
        "production_rust_consumer_qualified": False,
        "production_node_pipeline_qualified": False,
        "release_qualified": False,
    }
    try:
        before = kafka_committed(bootstrap)
        if before >= 0:
            raise Rejected("test_kafka_group_not_fresh")
        node_fixture_install(original_node, crash=True)
        first = native_once(bootstrap, binary, scratch, crash=True)
        if first.get("node_exit_code") != 73:
            raise Rejected("hard_crash_after_disk_not_observed")
        first_rows = disk_rows(binary, scratch)
        after_crash = kafka_committed(bootstrap)
        if after_crash >= 0:
            raise Rejected("kafka_offset_committed_despite_missing_grpc_ack")
        node_fixture_install(original_node, crash=False)
        second = native_once(bootstrap, binary, scratch, crash=False)
        if (second.get("valid_original_rust_commit_receipt") is not True
                or not base.approved_node_stop(
                    second.get("stop_receipt", {}), second.get("node_exit_code")
                )):
            raise Rejected("original_rust_or_node_recovery_ack_not_proven")
        second_rows = disk_rows(binary, scratch)
        after_replay = kafka_committed(bootstrap)
        if second_rows != first_rows or after_replay != 3:
            raise Rejected("kafka_redelivery_or_duplicate_row_check_failed")
        receipt.update({
            "actual_ack_loss_replay_qualified": True,
            "node_crash_after_disk_before_ack_exit": 73,
            "offset_uncommitted_after_node_crash": True,
            "original_rust_replayed_and_committed_offset": after_replay,
            "synthetic_persisted_event_count": len(second_rows),
            "recovery_node_grpc_ack_received": second.get("valid_original_rust_commit_receipt") is True,
            "test_only_recovery_no_reinsert": True,
        })
    except (Rejected, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        receipt["blocker"] = str(exc) if isinstance(exc, Rejected) else type(exc).__name__
    return receipt


def qualify(scratch: Path) -> dict[str, object]:
    started = time.monotonic()
    report: dict[str, object] = {
        "phase": "native_rust_kafka_node_ack_lost_durable_disk_replay_synthetic",
        "real_ack_lost_replay_integration_pass": False,
        "production_rust_ingestion_consumer_qualified": False,
        "production_node_ingestion_driver_qualified": False,
        "exactly_once_product_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    original_node = b""
    try:
        if (scratch.is_symlink() or scratch.exists()
                or scratch.parent.resolve() != Path("/private/tmp").resolve()
                or not scratch.name.startswith("flind-wave191-")):
            raise Rejected("unsafe_or_preexisting_wave191_scratch")
        original_path = base.ROOT / "tools/flind/verify_native_kafka_node_durable_wave190.mjs"
        if original_path.is_symlink() or not original_path.is_file():
            raise Rejected("missing_original_tracked_node_fixture")
        original_node = original_path.read_bytes()
        derived_fixture(original_node, crash=True)
        derived_fixture(original_node, crash=False)
        # Wave190's initializer restricts the path to wave190-prefix scratch.
        # Maintain that invariant by creating a separately scoped Wave191
        # scratch with the inherited Kafka/ClickHouse safety markers.
        scratch.mkdir()
        (scratch / ".flind-clickhouse-local-v1").write_text("FLIND_CLICKHOUSE_LOCAL_SCRATCH_V1\n")
        (scratch / ".flind-wave189-owner").write_text("FLIND_WAVE189_DURABLE_KAFKA_V1\n")
        (scratch / ".flind-wave190-owner").write_text("FLIND_WAVE190_KAFKA_RUST_NODE_DURABLE_V1\n")
        (scratch / OWNER).write_text(OWNER_VALUE)
        base.SCRATCH = scratch
        base.verify_first_party_fixture()
        report["original_node_source_sha1"] = base.node_attest.original_sources(base.REF, base.NODE)
        runtime, _schema = attested_supported_runtime(base.REF, scratch, base.CH_ASSET)
        broker = kafka_qualify(
            base.REF, base.KAFKA, scratch, clickhouse=str(runtime),
            on_broker_ready=lambda bootstrap, private:
                test_broker(bootstrap, runtime, scratch, original_node),
        )
        child = broker.get("optional_private_kafka_probe") or {}
        report["child"] = child
        report["owned_kafka_stopped"] = broker.get("owned_kafka_process_stopped") is True
        report["owned_kafka_scratch_removed"] = broker.get("owned_kafka_scratch_removed") is True
        report["real_ack_lost_replay_integration_pass"] = all((
            broker.get("real_kafka_producer_ack_qualified") is True,
            broker.get("real_kafka_consumer_qualified") is True,
            broker.get("local_clickhouse_relay_qualified") is True,
            child.get("actual_ack_loss_replay_qualified") is True,
            report["owned_kafka_stopped"],
            report["owned_kafka_scratch_removed"],
        ))
        if not report["real_ack_lost_replay_integration_pass"]:
            raise Rejected(child.get("blocker") or broker.get("blocker")
                           or "native_crash_replay_integration_not_qualified")
    except (Rejected, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        report["blocker"] = str(exc) if isinstance(exc, Rejected) else type(exc).__name__
    finally:
        # Never leave a fault-injected Node server fixture installed in the
        # shared disposable test scratch on a failed run.
        if original_node:
            path = base.NODE / "server-kafka-durable-wire.mjs"
            if path.is_file() and not path.is_symlink():
                path.write_bytes(original_node)
                # Also restore the compiled JS bundle, not merely its source.
                try:
                    built = subprocess.run(
                        ["node", "build-kafka-durable-wire.mjs"], cwd=base.NODE,
                        stdin=subprocess.DEVNULL, capture_output=True, timeout=16,
                    )
                    report["original_node_test_bundle_restored"] = (
                        built.returncode == 0 and
                        b"FLIND_WAVE190_ORIGINAL_NODE_SERVER_BUNDLE_PASS" in built.stdout
                    )
                except (OSError, subprocess.TimeoutExpired):
                    report["original_node_test_bundle_restored"] = False
                if not report["original_node_test_bundle_restored"]:
                    report["real_ack_lost_replay_integration_pass"] = False
                    report["blocker"] = "original_node_test_bundle_not_restored"
        report["elapsed_seconds"] = round(time.monotonic() - started, 1)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    a = parser.parse_args()
    r = qualify(a.scratch)
    print(json.dumps(r, indent=2, sort_keys=True) if a.json else
          "Flind native Kafka ack-loss synthetic replay: "
          + ("PASS" if r["real_ack_lost_replay_integration_pass"] else "BLOCKED"))
    return 0 if r["real_ack_lost_replay_integration_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
