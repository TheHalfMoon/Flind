#!/usr/bin/env python3
"""Actual supported ClickHouse 25.12 MergeTree across four process lifetimes.

Synthetic-only, tracked Flind events_recent subset. No Kafka native ingestion,
authenticated tenant authorization, production server or release claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import (
    EXPECTED_COLUMNS, FIELDS, ProbeBlocked, checked_scratch,
    fixture, scoped_sql, verified_schema,
)
from tools.flind.qualify_local_clickhouse_insert_wave178 import insert_sql
from tools.flind.qualify_supported_clickhouse_kafka_wave181 import (
    source_clickhouse_spec, binary_clickhouse_version, version_qualified,
)

EXPECTED_VERSION = "25.12.7.21"
OFFICIAL_MAC_ARM64_SHA256 = "e5be46727e773893b5786aaa3d28f5661a30179fe65e19096d8eb7d41a554fd6"
OWNER_FILE = ".flind-wave188-owner"
OWNER_TEXT = "FLIND_WAVE188_CLICKHOUSE_SUPPORTED_DURABLE_V1\n"
FREE_DISK_FLOOR = 5 * 1024**3


class Refused(ValueError):
    pass


def checked_runtime(repo: Path, scratch: Path, binary: Path) -> tuple[str, dict[str, str], Path]:
    checked_scratch(repo, scratch, "HEAD")
    marker = scratch / OWNER_FILE
    if marker.is_symlink() or not marker.is_file() or marker.read_text() != OWNER_TEXT:
        raise Refused("not_owned_wave188_scratch")
    if binary.is_symlink() or not binary.is_file() or binary.resolve().parent != scratch.resolve():
        raise Refused("unsupported_clickhouse_binary_scope")
    if shutil.disk_usage(scratch).free < FREE_DISK_FLOOR:
        raise Refused("insufficient_disk_reserve")
    if binary.stat().st_size != 123762120:
        raise Refused("clickhouse_official_asset_size_mismatch")
    with binary.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != OFFICIAL_MAC_ARM64_SHA256:
        raise Refused("clickhouse_official_asset_digest_mismatch")
    # The official Mac asset self-unpacks into a larger executable on its
    # first invocation. Keep the SHA256-attested download *immutable* and run
    # a newly created disposable copy; otherwise --version alters the asset
    # bytes and incorrectly invalidates reproducible supply-chain evidence.
    runtime_binary = scratch / "wave188-unpacked-clickhouse-runtime"
    if runtime_binary.exists() or runtime_binary.is_symlink():
        raise Refused("clickhouse_runtime_copy_conflict")
    shutil.copyfile(binary, runtime_binary)
    runtime_binary.chmod(0o700)
    # GitHub's compressed macOS asset may spend >9s performing its first
    # self-extraction. Allow 45s ONLY for that bootstrap; steady SQL process
    # invocations remain strictly bounded at 27s each.
    try:
        first_boot = subprocess.run(
            [str(runtime_binary), "--version"], stdin=subprocess.DEVNULL,
            capture_output=True, timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("clickhouse_official_first_bootstrap_failed") from exc
    if first_boot.returncode or len(first_boot.stdout) > 1000:
        raise Refused("clickhouse_official_first_bootstrap_failed")
    version = binary_clickhouse_version(runtime_binary)
    sha, supported = source_clickhouse_spec(repo)
    if version != EXPECTED_VERSION or not version_qualified(version, supported):
        raise Refused("clickhouse_binary_outside_source_supported_range")
    schema_sha, schema = verified_schema(repo, "HEAD")
    if schema_sha != sha or schema != EXPECTED_COLUMNS:
        raise Refused("first_party_event_schema_version_mismatch")
    return sha, schema, runtime_binary


def process_query(binary: Path, scratch: Path, session: Path,
                  statement: str, index: int) -> list[dict]:
    if not 1 <= index <= 4:
        raise Refused("session_count_budget")
    output, error = (scratch / f"wave188-process-{index}.jsonl",
                     scratch / f"wave188-process-{index}.stderr")
    if output.exists() or output.is_symlink() or error.exists() or error.is_symlink():
        raise Refused("unowned_clickhouse_process_output")
    cmd = [
        str(binary), "local", "--multiquery", "--path", str(session),
        "--max_memory_usage=134217728", "--max_threads=2",
        "--query", statement,
    ]
    try:
        with output.open("xb") as out, error.open("xb") as err:
            result = subprocess.run(cmd, cwd=scratch, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err,
                                    check=False, timeout=27,
                                    env={**os.environ, "HOME": str(scratch),
                                         "CLICKHOUSE_WATCHDOG_ENABLE": "0"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("clickhouse_mergetree_process_timeout_or_failure") from exc
    if result.returncode or output.stat().st_size > 24000 or error.stat().st_size > 8000:
        raise Refused("actual_clickhouse_mergetree_sql_process_failed")
    try:
        return [json.loads(line) for line in output.read_text().splitlines() if line]
    except (ValueError, UnicodeError) as exc:
        raise Refused("clickhouse_mergetree_unparseable_output") from exc


def qualify(repo: Path, scratch: Path, binary: Path) -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "supported_clickhouse_2512_mergetree_durable_process_restart",
        "official_supported_binary_attested": False,
        "first_party_events_schema_attested": False,
        "real_supported_mergetree_insert_qualified": False,
        "mergetree_persisted_across_four_processes": False,
        "synthetic_team_predicates_after_restart_qualified": False,
        "native_kafka_to_clickhouse_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "sdk_api_dashboard_qualified": False,
        "release_qualified": False,
    }
    started = time.monotonic()
    try:
        sha, schema, runtime_binary = checked_runtime(repo, scratch, binary)
        report["first_party_source_commit"] = sha
        report["official_supported_binary_attested"] = True
        report["first_party_events_schema_attested"] = True
        report["supported_clickhouse_version"] = EXPECTED_VERSION
        session = scratch / "wave188-durable-session"
        if session.exists() or session.is_symlink():
            raise Refused("persisted_session_already_exists")
        original = fixture()
        ddl = ", ".join(f"{col} {schema[col]}" for col in FIELDS)
        count101 = scoped_sql(101, kind="counts")
        count202 = scoped_sql(202, kind="counts")
        count303 = scoped_sql(303, kind="counts")
        uuids = ("SELECT uuid, team_id, event FROM events "
                 "ORDER BY uuid FORMAT JSONEachRow")
        stage1 = process_query(
            runtime_binary, scratch, session,
            f"CREATE TABLE events ({ddl}) ENGINE = MergeTree "
            f"ORDER BY (team_id, timestamp, uuid);"
            + insert_sql(original, schema)
            + ";" + count101 + ";" + count202 + ";",
            1,
        )
        if stage1 != [
            {"team_id": 101, "event_count": 2},
            {"team_id": 202, "event_count": 2},
        ]:
            raise Refused("mergetree_initial_insert_counts_mismatch")
        report["real_supported_mergetree_insert_qualified"] = True
        stage2 = process_query(runtime_binary, scratch, session, uuids + ";", 2)
        if [(r.get("uuid"), r.get("team_id"), r.get("event")) for r in stage2] != sorted(
            [(r["uuid"], r["team_id"], r["event"]) for r in original]
        ):
            raise Refused("initial_mergetree_restart_uuid_readback_mismatch")
        fifth = {
            "uuid": "00000000-0000-4000-8000-000000000005",
            "team_id": 101,
            "event": "flind_team_a_return",
            "distinct_id": "a-demo",
            "properties": "{}",
            "timestamp": "2026-10-27 12:04:00.000000",
        }
        stage3 = process_query(
            runtime_binary, scratch, session,
            insert_sql([fifth], schema) + ";" + count101 + ";", 3,
        )
        if stage3 != [{"team_id": 101, "event_count": 3}]:
            raise Refused("second_process_lifecycle_insert_failed")
        stage4 = process_query(
            runtime_binary, scratch, session,
            count101 + ";" + count202 + ";" + count303 + ";" + uuids + ";", 4,
        )
        counts = [row for row in stage4 if "event_count" in row]
        events = [row for row in stage4 if "uuid" in row]
        if counts != [
            {"team_id": 101, "event_count": 3},
            {"team_id": 202, "event_count": 2},
        ] or len(events) != 5 or any(row.get("team_id") not in (101, 202) for row in events):
            raise Refused("durable_mergetree_team_counts_mismatch")
        expected = {r["uuid"]: r for r in [*original, fifth]}
        if set(row.get("uuid") for row in events) != set(expected):
            raise Refused("durable_mergetree_event_uuid_mismatch")
        if any(row["team_id"] != expected[row["uuid"]]["team_id"]
               or row["event"] != expected[row["uuid"]]["event"] for row in events):
            raise Refused("durable_mergetree_event_content_mismatch")
        # Check that the source-backed MergeTree actually wrote part files.
        store = session / "store"
        if not store.is_dir() or not any(
            p.name == "checksums.txt" for p in store.rglob("checksums.txt")
        ):
            raise Refused("mergetree_disk_part_checksum_unavailable")
        report["mergetree_persisted_across_four_processes"] = True
        report["synthetic_team_predicates_after_restart_qualified"] = True
        report["synthetic_events_persisted"] = 5
        report["synthetic_teams_checked"] = [101, 202, 303]
        report["real_clickhouse_processes_executed"] = 4
        report["disk_part_checksum_present"] = True
    except (Refused, ProbeBlocked) as exc:
        report["blocker"] = str(exc)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report["blocker"] = type(exc).__name__
    report["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--clickhouse", type=Path, required=True)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    result = qualify(a.repo, a.scratch, a.clickhouse)
    if a.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Flind official supported MergeTree durability:",
              "PASS" if result["mergetree_persisted_across_four_processes"] else "BLOCKED")
    return 0 if result["mergetree_persisted_across_four_processes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
