#!/usr/bin/env python3
"""Real Kafka4.3.1 -> synthetic-only Python bridge -> supported durable MergeTree.

Consumes the exact Kafka records from Wave179 using a SECOND consumer group.
Only commits its own Kafka offset *after* a separate ClickHouse process
reopens persistent MergeTree and verifies all synthetic UUIDs. Not first-party
Rust Kafka worker or production Node ingestion pipeline; release remains NO-GO.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import (
    TOPIC, EVENTS, SAFE_BROKER, readback_accepted, qualify as real_kafka,
)
from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import (
    FIELDS, EXPECTED_COLUMNS, checked_scratch, verified_schema, scoped_sql,
)
from tools.flind.qualify_local_clickhouse_insert_wave178 import insert_sql
from tools.flind.qualify_supported_mergetree_durable_wave188 import (
    OFFICIAL_MAC_ARM64_SHA256, EXPECTED_VERSION,
)
from tools.flind.qualify_supported_clickhouse_kafka_wave181 import (
    source_clickhouse_spec, version_qualified, binary_clickhouse_version,
)

OWNER = ".flind-wave189-owner"
OWNER_VALUE = "FLIND_WAVE189_DURABLE_KAFKA_V1\n"
FIXTURE_GROUP = "flind-wave189-committed-after-disk-readback"


class Refused(ValueError):
    pass


def attested_supported_runtime(repo: Path, scratch: Path, source_asset: Path) -> tuple[Path, dict[str, str]]:
    checked_scratch(repo, scratch, "HEAD")
    mark = scratch / OWNER
    if mark.is_symlink() or not mark.is_file() or mark.read_text() != OWNER_VALUE:
        raise Refused("unowned_wave189_scratch")
    if (source_asset.is_symlink() or not source_asset.is_file()
            or source_asset.name != "clickhouse-original-compressed-aarch64"
            or source_asset.parent != Path("/private/tmp/flind-wave188-ch2512-durable")):
        raise Refused("untrusted_clickhouse_official_asset_source")
    with source_asset.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if source_asset.stat().st_size != 123762120 or digest != OFFICIAL_MAC_ARM64_SHA256:
        raise Refused("clickhouse_official_compressed_asset_modified")
    if shutil.disk_usage(scratch).free < 5 * 1024**3:
        raise Refused("scratch_disk_reserve_below_five_gib")
    commit, schema = verified_schema(repo, "HEAD")
    spec_commit, spec = source_clickhouse_spec(repo)
    if commit != spec_commit or schema != EXPECTED_COLUMNS:
        raise Refused("source_schema_or_version_commit_mismatch")
    runbinary = scratch / "wave189-runtime-clickhouse"
    if runbinary.exists() or runbinary.is_symlink():
        raise Refused("clickhouse_runtime_conflict")
    shutil.copyfile(source_asset, runbinary)
    runbinary.chmod(0o700)
    try:
        opened = subprocess.run([str(runbinary), "--version"],
                                stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("official_clickhouse_first_boot_failed") from exc
    if opened.returncode or len(opened.stdout) > 1000:
        raise Refused("official_clickhouse_first_boot_failed")
    observed = binary_clickhouse_version(runbinary)
    if observed != EXPECTED_VERSION or not version_qualified(observed, spec):
        raise Refused("clickhouse_outside_first_party_supported_version")
    return runbinary, schema


def kafka_record_projection(records: list[dict]) -> list[dict[str, object]]:
    if not readback_accepted(records):
        raise Refused("unapproved_kafka_fixture_or_order")
    rows: list[dict[str, object]] = []
    for i, source in enumerate(records):
        rows.append({
            "uuid": str(UUID(int=18901 + i)),
            "event": source["event"],
            "properties": json.dumps(source["properties"], sort_keys=True, separators=(",", ":")),
            "timestamp": f"2026-10-27 12:10:0{i}.000000",
            "team_id": source["team_id"],
            "distinct_id": source["distinct_id"],
        })
    if len(rows) != 3 or {r["team_id"] for r in rows} != {101, 202}:
        raise Refused("synthetic_team_projection_invalid")
    return rows


def ch_process(binary: Path, scratch: Path, session: Path, sql: str, ordinal: int) -> list[dict]:
    if ordinal not in (1, 2):
        raise Refused("clickhouse_two_process_budget")
    stdout = scratch / f"wave189-clickhouse-{ordinal}.jsonl"
    stderr = scratch / f"wave189-clickhouse-{ordinal}.err"
    if any(p.exists() or p.is_symlink() for p in (stdout, stderr)):
        raise Refused("unowned_clickhouse_output_conflict")
    try:
        with stdout.open("xb") as out, stderr.open("xb") as err:
            done = subprocess.run(
                [str(binary), "local", "--multiquery", "--path", str(session),
                 "--max_memory_usage=134217728", "--max_threads=2", "--query", sql],
                cwd=scratch, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                check=False, timeout=27, env={**os.environ, "HOME": str(scratch)},
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("clickhouse_persistent_process_timeout") from exc
    if done.returncode or stdout.stat().st_size > 30000 or stderr.stat().st_size > 8000:
        raise Refused("clickhouse_persistent_process_failed")
    try:
        return [json.loads(line) for line in stdout.read_text().splitlines() if line]
    except (UnicodeError, ValueError) as exc:
        raise Refused("invalid_clickhouse_persistent_response") from exc


def disk_persist_and_reopen(binary: Path, scratch: Path, schema: dict,
                            records: list[dict]) -> dict[str, object]:
    rows = kafka_record_projection(records)
    session = scratch / "wave189-mergetree-state"
    if session.exists() or session.is_symlink():
        raise Refused("existing_mergetree_state_refused")
    spec = ", ".join(f"{field} {schema[field]}" for field in FIELDS)
    first = ch_process(
        binary, scratch, session,
        f"CREATE TABLE events ({spec}) ENGINE=MergeTree "
        "ORDER BY (team_id, timestamp, uuid);"
        + insert_sql(rows, schema) + ";"
        + scoped_sql(101, kind="counts") + ";"
        + scoped_sql(202, kind="counts") + ";", 1,
    )
    if first != [{"team_id": 101, "event_count": 2},
                 {"team_id": 202, "event_count": 1}]:
        raise Refused("kafka_mergetree_insert_team_count_mismatch")
    select = ("SELECT uuid,team_id,event FROM events ORDER BY uuid FORMAT JSONEachRow")
    second = ch_process(
        binary, scratch, session,
        scoped_sql(101, kind="counts") + ";"
        + scoped_sql(202, kind="counts") + ";"
        + scoped_sql(303, kind="counts") + ";"
        + select + ";", 2,
    )
    count_rows = [row for row in second if "event_count" in row]
    event_rows = [row for row in second if "uuid" in row]
    if count_rows != first:
        raise Refused("kafka_durable_restart_count_mismatch")
    projected = [{name: r[name] for name in ("uuid", "team_id", "event")} for r in rows]
    if event_rows != sorted(projected, key=lambda r: r["uuid"]):
        raise Refused("kafka_durable_restart_uuid_mismatch")
    if not (session / "store").is_dir() or not any(
        p.name == "checksums.txt" for p in (session / "store").rglob("checksums.txt")
    ):
        raise Refused("kafka_durable_disk_parts_not_written")
    return {
        "kafka_consumed_records_persisted": 3,
        "two_independent_clickhouse_processes_qualified": True,
        "kafka_mergetree_same_uuids_verified_after_restart": True,
        "durable_synthetic_team_101": 2,
        "durable_synthetic_team_202": 1,
        "durable_synthetic_team_303": 0,
        "native_rust_worker_qualified": False,
        "node_production_pipeline_qualified": False,
        "release_qualified": False,
    }


def callback(bootstrap: str, binary: Path, scratch: Path, schema: dict) -> dict[str, object]:
    report: dict[str, object] = {
        "kafka_durable_relay_and_offset_commit_pass": False,
        "actual_kafka_offset_committed_after_disk_readback": False,
        "production_kafka_ingestion_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    consumer = None
    try:
        if not SAFE_BROKER.fullmatch(bootstrap) or schema != EXPECTED_COLUMNS:
            raise Refused("unsafe_private_kafka_or_schema")
        from confluent_kafka import Consumer
        consumer = Consumer({
            "bootstrap.servers": bootstrap, "group.id": FIXTURE_GROUP,
            "auto.offset.reset": "earliest", "enable.auto.commit": False,
            "session.timeout.ms": 7000, "client.id": "flind-wave189-durable-replay",
        })
        consumer.subscribe([TOPIC])
        records = []
        deadline = time.monotonic() + 22
        while len(records) < 3 and time.monotonic() < deadline:
            message = consumer.poll(0.7)
            if message is None:
                continue
            if message.error():
                raise Refused("private_kafka_message_error")
            raw = message.value()
            if not isinstance(raw, bytes) or len(raw) > 2048:
                raise Refused("invalid_or_oversized_kafka_payload")
            records.append(json.loads(raw))
        if not readback_accepted(records):
            raise Refused("private_kafka_record_validation_failed")
        persisted = disk_persist_and_reopen(binary, scratch, schema, records)
        # A callback must never be able to commit just because it returned an
        # empty or forged "success" dict. Require exact durable readback and
        # immutable negative product/release flags.
        if (type(persisted) is not dict
                or persisted.get("kafka_consumed_records_persisted") != 3
                or persisted.get("two_independent_clickhouse_processes_qualified") is not True
                or persisted.get("kafka_mergetree_same_uuids_verified_after_restart") is not True
                or persisted.get("native_rust_worker_qualified") is not False
                or persisted.get("node_production_pipeline_qualified") is not False
                or persisted.get("release_qualified") is not False):
            raise Refused("durable_clickhouse_readback_receipt_not_verified")
        report.update(persisted)
        # Commit is intentionally after successful disk readback, but this
        # does NOT guarantee production exactly-once semantics or crash replay.
        consumer.commit(asynchronous=False)
        report["actual_kafka_offset_committed_after_disk_readback"] = True
        report["kafka_durable_relay_and_offset_commit_pass"] = True
    except Exception as exc:
        # Do not serialize arbitrary Kafka messages or exception content.
        report["blocker"] = str(exc) if isinstance(exc, Refused) else type(exc).__name__
    finally:
        if consumer is not None:
            consumer.close()
    return report


def qualify(repo: Path, kafka_home: Path, scratch: Path, compressed_asset: Path) -> dict:
    result: dict[str, object] = {
        "phase": "actual_private_kafka_to_persistent_supported_mergetree_synthetic_relay",
        "official_supported_clickhouse_attested": False,
        "real_kafka_to_durable_mergetree_relay_qualified": False,
        "real_first_party_rust_consumer_qualified": False,
        "real_node_production_driver_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "sdk_api_dashboard_qualified": False,
        "release_qualified": False,
    }
    started = time.monotonic()
    try:
        runbinary, schema = attested_supported_runtime(repo, scratch, compressed_asset)
        result["official_supported_clickhouse_attested"] = True
        parent = real_kafka(
            repo, kafka_home, scratch, clickhouse=str(runbinary),
            on_broker_ready=lambda bootstrap, owned: callback(bootstrap, runbinary, scratch, schema),
        )
        child = parent.get("optional_private_kafka_probe") or {}
        result["real_kafka_to_durable_mergetree_relay_qualified"] = all((
            parent.get("kafka_431_broker_qualified") is True,
            parent.get("real_kafka_producer_ack_qualified") is True,
            parent.get("real_kafka_consumer_qualified") is True,
            parent.get("local_clickhouse_relay_qualified") is True,
            child.get("kafka_durable_relay_and_offset_commit_pass") is True,
            child.get("actual_kafka_offset_committed_after_disk_readback") is True,
            parent.get("owned_kafka_process_stopped") is True,
            parent.get("owned_kafka_scratch_removed") is True,
        ))
        result["actual_kafka_records_persisted"] = child.get("kafka_consumed_records_persisted", 0)
        result["kafka_offset_commit_after_disk_qualified"] = (
            child.get("actual_kafka_offset_committed_after_disk_readback") is True
        )
        result["owned_kafka_process_stopped"] = parent.get("owned_kafka_process_stopped")
        result["owned_kafka_scratch_removed"] = parent.get("owned_kafka_scratch_removed")
        if not result["real_kafka_to_durable_mergetree_relay_qualified"]:
            raise Refused(child.get("blocker") or parent.get("blocker")
                          or "kafka_durable_mergetree_chain_not_qualified")
    except (Refused, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["blocker"] = str(exc) if isinstance(exc, Refused) else type(exc).__name__
    result["elapsed_seconds"] = round(time.monotonic() - started, 1)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--kafka-home", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--compressed-clickhouse", type=Path, required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    output = qualify(args.repo, args.kafka_home, args.scratch, args.compressed_clickhouse)
    print(json.dumps(output, sort_keys=True, indent=2) if args.json else
          ("Flind real Kafka → supported persistent MergeTree: " +
           ("PASS" if output["real_kafka_to_durable_mergetree_relay_qualified"] else "BLOCKED")))
    return 0 if output["real_kafka_to_durable_mergetree_relay_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
