#!/usr/bin/env python3
"""Real isolated ClickHouse local INSERT and scoped SELECT with synthetic Flind events.

Use tracked first-party event field names/types, Memory engine, no daemon, Kafka,
SDK, authenticated API or real customer data. This is a bounded SQL smoke test.
"""
from __future__ import annotations

import argparse
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

MAX_STATEMENTS = 8


def insert_sql(rows: list[dict[str, object]], schema: dict[str, str]) -> str:
    if schema != EXPECTED_COLUMNS:
        raise ProbeBlocked("first_party_schema_not_verified")
    if not rows or len(rows) > 20:
        raise ProbeBlocked("synthetic_insert_row_budget")
    columns = ", ".join(FIELDS)
    values = []
    for row in rows:
        if set(row) != set(FIELDS) or row.get("team_id") not in (101, 202):
            raise ProbeBlocked("unexpected_synthetic_insert_shape")
        cells = []
        for name in FIELDS:
            value = row[name]
            if name == "team_id":
                if type(value) is not int:
                    raise ProbeBlocked("invalid_integer_team_id")
                cells.append(str(value))
            else:
                if not isinstance(value, str) or len(value) > 256 or "\x00" in value:
                    raise ProbeBlocked("invalid_synthetic_event_field")
                cells.append("'" + value.replace("\\", "\\\\").replace("'", "''") + "'")
        values.append("(" + ",".join(cells) + ")")
    return f"INSERT INTO events ({columns}) VALUES " + ",".join(values)


def query_plan(rows: list[dict[str, object]], schema: dict[str, str]) -> str:
    if schema != EXPECTED_COLUMNS:
        raise ProbeBlocked("first_party_schema_not_verified")
    ddl = ", ".join(f"{field} {schema[field]}" for field in FIELDS)
    statements = [
        f"CREATE TABLE events ({ddl}) ENGINE = Memory",
        insert_sql(rows, schema),
        scoped_sql(101, kind="counts"),
        scoped_sql(202, kind="counts"),
        scoped_sql(101, kind="events"),
        scoped_sql(202, kind="events"),
        scoped_sql(303, kind="counts"),
    ]
    if len(statements) > MAX_STATEMENTS:
        raise ProbeBlocked("query_plan_over_budget")
    return ";\n".join(statements) + ";\n"


def run_insert(root: Path, scratch: Path, ref: str = "HEAD",
               clickhouse: str | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "phase": "first-party-schema-clickhouse-memory-synthetic-insert",
        "source_ref": ref,
        "first_party_schema_verified": False,
        "real_clickhouse_insert_qualified": False,
        "synthetic_team_query_qualified": False,
        "mergetree_persistence_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "first_party_sdk_ingestion_qualified": False,
        "kafka_ingestion_qualified": False,
        "api_dashboard_qualified": False,
        "release_qualified": False,
    }
    start = time.monotonic()
    try:
        checked_scratch(root, scratch, ref)
        sha, schema = verified_schema(root, ref)
        result["source_commit"] = sha
        result["first_party_schema_verified"] = True
        executable = clickhouse or shutil.which("clickhouse")
        if not executable or not Path(executable).is_file():
            raise ProbeBlocked("clickhouse_not_found")
        local_session = scratch / "wave178-memory-session"
        if local_session.exists() or local_session.is_symlink():
            raise ProbeBlocked("memory_session_exists")
        rows = fixture()
        statements = query_plan(rows, schema)
        command = [
            executable, "local", "--multiquery",
            "--path", str(local_session),
            "--max_memory_usage=134217728",
            "--query", statements,
        ]
        # ClickHouse local in --multiquery mode can await stdin EOF when
        # launched as a standalone script. Explicitly detach stdin and use
        # scratch-only output files (not inherited PIPE handles).
        stdout_path = scratch / "wave178-local-output.jsonl"
        stderr_path = scratch / "wave178-local-errors.log"
        if stdout_path.exists() or stderr_path.exists():
            raise ProbeBlocked("clickhouse_scratch_output_conflict")
        try:
            with stdout_path.open("xb") as output_stream, stderr_path.open("xb") as error_stream:
                process = subprocess.run(
                    command, cwd=scratch, stdin=subprocess.DEVNULL,
                    stdout=output_stream, stderr=error_stream,
                    check=False, timeout=18, env={**os.environ, "HOME": str(scratch)},
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProbeBlocked("clickhouse_insert_process_failed_or_timed_out") from exc
        if (process.returncode or stdout_path.stat().st_size > 32_000
                or stderr_path.stat().st_size > 8_000):
            raise ProbeBlocked("real_clickhouse_insert_or_select_failed")
        try:
            output = [json.loads(line) for line in stdout_path.read_text().splitlines() if line]
        except (ValueError, UnicodeError) as exc:
            raise ProbeBlocked("invalid_clickhouse_query_output") from exc
        counts = [r for r in output if "event_count" in r]
        events = [r for r in output if "event" in r]
        if counts != [
            {"team_id": 101, "event_count": 2},
            {"team_id": 202, "event_count": 2},
        ]:
            raise ProbeBlocked("clickhouse_insert_counts_mismatch")
        if (len(events) != 4
                or len([r for r in events if r["team_id"] == 101]) != 2
                or len([r for r in events if r["team_id"] == 202]) != 2
                or any("team_b" in r["event"] for r in events if r["team_id"] == 101)
                or any("team_a" in r["event"] for r in events if r["team_id"] == 202)):
            raise ProbeBlocked("clickhouse_insert_cross_team_query_leak")
        result["real_clickhouse_insert_qualified"] = True
        result["synthetic_team_query_qualified"] = True
        result["synthetic_inserted_rows"] = len(rows)
        result["sql_statements_run"] = 7
        result["teams_checked"] = [101, 202]
    except ProbeBlocked as exc:
        result["blocker"] = str(exc)
    except (OSError, ValueError) as exc:
        result["blocker"] = type(exc).__name__
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - start, 1)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--clickhouse", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_insert(args.repo, args.scratch, args.ref, args.clickhouse)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Flind source-backed ClickHouse INSERT:",
              "PASS" if result["real_clickhouse_insert_qualified"] else "BLOCKED")
    return 0 if result["real_clickhouse_insert_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
