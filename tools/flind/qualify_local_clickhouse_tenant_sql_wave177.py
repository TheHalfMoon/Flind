#!/usr/bin/env python3
"""Qualify synthetic per-team ClickHouse SQL against the tracked Flind events schema.

Offline ClickHouse local, no server, Kafka, customer data, credentials or API.
Queries are always constrained by a validated numeric team_id. Never implies
authenticated authorization, real ingestion or release qualification.
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
import tempfile
import time

SCHEMA_PATH = "posthog/clickhouse/hcl/roles/coshared/events_recent/tables.hcl"
SCRATCH_MARKER = ".flind-clickhouse-local-v1"
SCRATCH_MARKER_TEXT = "FLIND_CLICKHOUSE_LOCAL_SCRATCH_V1\n"
EXPECTED_COLUMNS = {
    "uuid": "UUID", "event": "String", "properties": "String",
    "timestamp": "DateTime64(6, 'UTC')", "team_id": "Int64",
    "distinct_id": "String",
}
FIELDS = tuple(EXPECTED_COLUMNS)
MAX_SOURCE_BYTES = 128 * 1024
SAFE_REF = re.compile(r"[A-Za-z0-9_./-]{1,128}\Z")
BOUNDARY = Path("/private/tmp")


class ProbeBlocked(Exception):
    pass


def accept_team(team_id: object) -> int:
    """Prevent injected SQL, booleans, negatives and unbounded integers."""
    if type(team_id) is not int or not 1 <= team_id <= 2**63 - 1:
        raise ProbeBlocked("invalid_team_identifier")
    return team_id


def checked_scratch(repo: Path, scratch: Path, ref: str) -> None:
    try:
        if not SAFE_REF.fullmatch(ref) or ref.startswith("-") or ".." in ref.split("/"):
            raise ProbeBlocked("invalid_source_ref")
        boundary = BOUNDARY.resolve()
        for folder in (repo, scratch):
            if (folder.is_symlink() or not folder.is_dir()
                    or boundary not in folder.resolve().parents):
                raise ProbeBlocked("unsafe_source_or_scratch")
        if scratch.resolve() == repo.resolve() or (
            repo.resolve() in scratch.resolve().parents or
            scratch.resolve() in repo.resolve().parents
        ):
            raise ProbeBlocked("source_scratch_overlap")
        marker = scratch / SCRATCH_MARKER
        if marker.is_symlink() or not marker.is_file() or marker.read_text() != SCRATCH_MARKER_TEXT:
            raise ProbeBlocked("scratch_marker_missing")
        if not (repo / ".git").exists() or not (repo / "pyproject.toml").is_file():
            raise ProbeBlocked("first_party_repo_missing")
    except (OSError, UnicodeError) as exc:
        raise ProbeBlocked("source_scratch_preflight_failed") from exc


def verified_schema(repo: Path, ref: str) -> tuple[str, dict[str, str]]:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_OPTIONAL_LOCKS": "0"}
    try:
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", ref + "^{commit}"],
            capture_output=True, check=False, timeout=20, env=env,
        )
        commit = sha.stdout.decode("ascii").strip()
        if sha.returncode or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise ProbeBlocked("first_party_source_commit_missing")
        tree = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", ref, "--", SCHEMA_PATH],
            capture_output=True, check=False, timeout=20, env=env,
        )
        metadata = tree.stdout.decode("utf-8").strip().split()
        if tree.returncode or len(metadata) != 4 or metadata[:2] != ["100644", "blob"]:
            raise ProbeBlocked("source_schema_not_tracked_blob")
        oid = metadata[2]
        blob = subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{SCHEMA_PATH}"],
            capture_output=True, check=False, timeout=35, env=env,
        )
        data = blob.stdout
        if blob.returncode or len(data) > MAX_SOURCE_BYTES:
            raise ProbeBlocked("source_schema_blob_unavailable")
        computed = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if computed != oid:
            raise ProbeBlocked("source_schema_blob_digest_mismatch")
        text = data.decode("utf-8")
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ProbeBlocked("offline_source_schema_unavailable") from exc
    try:
        columns = {}
        for name, field_type in re.findall(
            r'column\s+"([a-zA-Z0-9_]+)"\s*\{\s*type\s*=\s*"([^"]+)"',
            text,
        ):
            if name in EXPECTED_COLUMNS:
                if name in columns:
                    raise ProbeBlocked("duplicate_source_schema_column")
                columns[name] = field_type
        if columns != EXPECTED_COLUMNS or 'table "events_recent"' not in text:
            raise ProbeBlocked("first_party_events_schema_mismatch")
    except UnicodeError as exc:
        raise ProbeBlocked("invalid_first_party_schema_encoding") from exc
    return commit, columns


def scoped_sql(team_id: int, *, kind: str) -> str:
    team = accept_team(team_id)
    if kind == "events":
        return (f"SELECT team_id, event, distinct_id FROM events "
                f"WHERE team_id = {team} ORDER BY event, distinct_id FORMAT JSONEachRow")
    if kind == "counts":
        return (f"SELECT team_id, count() AS event_count FROM events "
                f"WHERE team_id = {team} GROUP BY team_id ORDER BY team_id FORMAT JSONEachRow")
    raise ProbeBlocked("unsupported_query_kind")


def fixture() -> list[dict[str, object]]:
    return [
        {"uuid": "00000000-0000-4000-8000-000000000001", "team_id": 101,
         "event": "flind_team_a_signup", "distinct_id": "a-demo", "properties": "{}",
         "timestamp": "2026-10-27 12:00:00.000000"},
        {"uuid": "00000000-0000-4000-8000-000000000002", "team_id": 202,
         "event": "flind_team_b_private_event", "distinct_id": "b-demo", "properties": "{}",
         "timestamp": "2026-10-27 12:01:00.000000"},
        {"uuid": "00000000-0000-4000-8000-000000000003", "team_id": 101,
         "event": "flind_team_a_pageview", "distinct_id": "a-demo", "properties": "{}",
         "timestamp": "2026-10-27 12:02:00.000000"},
        {"uuid": "00000000-0000-4000-8000-000000000004", "team_id": 202,
         "event": "flind_team_b_pageview", "distinct_id": "b-demo", "properties": "{}",
         "timestamp": "2026-10-27 12:03:00.000000"},
    ]


def execute_local(clickhouse: str, scratch: Path, dataset: Path,
                  schema: dict[str, str], statement: str, ordinal: int) -> list[dict]:
    # Each query receives a wholly separate local-engine state directory.
    local_path = scratch / f"clickhouse-query-{ordinal}"
    if local_path.exists() or local_path.is_symlink():
        raise ProbeBlocked("clickhouse_scratch_session_conflict")
    field_spec = ", ".join(f"{name} {schema[name]}" for name in FIELDS)
    args = [
        clickhouse, "local",
        "--path", str(local_path),
        "--table", "events",
        "--file", str(dataset),
        "--structure", field_spec,
        "--input-format", "JSONEachRow",
        "--max_memory_usage=134217728",
        "--query", statement,
    ]
    try:
        run = subprocess.run(
            args, capture_output=True, check=False, timeout=30,
            env={**os.environ, "HOME": str(scratch), "CLICKHOUSE_WATCHDOG_ENABLE": "0"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeBlocked("local_clickhouse_process_unavailable") from exc
    if run.returncode or len(run.stdout) > 64_000:
        raise ProbeBlocked("local_clickhouse_query_failed")
    try:
        return [json.loads(line) for line in run.stdout.decode("utf-8").splitlines() if line]
    except (UnicodeError, ValueError) as exc:
        raise ProbeBlocked("invalid_clickhouse_query_receipt") from exc


def qualify(repo: Path, scratch: Path, ref: str = "HEAD",
            clickhouse: str | None = None) -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "source-backed-synthetic-clickhouse-tenant-predicate",
        "source_ref": ref,
        "schema_from_tracked_flind": False,
        "clickhouse_local_engine_qualified": False,
        "synthetic_team_predicates_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "kafka_ingestion_qualified": False,
        "flind_sdk_ingestion_qualified": False,
        "api_dashboard_qualified": False,
        "release_qualified": False,
    }
    started = time.monotonic()
    try:
        checked_scratch(repo, scratch, ref)
        source_commit, columns = verified_schema(repo, ref)
        report["source_commit"] = source_commit
        report["schema_from_tracked_flind"] = True
        executable = clickhouse or shutil.which("clickhouse")
        if not executable or not Path(executable).is_file():
            raise ProbeBlocked("local_clickhouse_executable_missing")
        if (scratch / "events.jsonl").exists():
            raise ProbeBlocked("scratch_event_fixture_conflict")
        rows = fixture()
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=scratch,
            prefix="flind-events-", suffix=".jsonl", delete=False,
        ) as handle:
            dataset = Path(handle.name)
            for item in rows:
                handle.write(json.dumps(item, separators=(",", ":")) + "\n")
        try:
            counts_a = execute_local(
                executable, scratch, dataset, columns, scoped_sql(101, kind="counts"), 0,
            )
            counts_b = execute_local(
                executable, scratch, dataset, columns, scoped_sql(202, kind="counts"), 1,
            )
            events_a = execute_local(
                executable, scratch, dataset, columns, scoped_sql(101, kind="events"), 2,
            )
            events_b = execute_local(
                executable, scratch, dataset, columns, scoped_sql(202, kind="events"), 3,
            )
            absent = execute_local(
                executable, scratch, dataset, columns, scoped_sql(303, kind="counts"), 4,
            )
        finally:
            dataset.unlink(missing_ok=True)
        report["clickhouse_local_engine_qualified"] = True
        if (counts_a != [{"team_id": 101, "event_count": 2}]
                or counts_b != [{"team_id": 202, "event_count": 2}]
                or absent):
            raise ProbeBlocked("synthetic_team_count_mismatch")
        if (len(events_a) != 2 or len(events_b) != 2
                or {row["team_id"] for row in events_a} != {101}
                or {row["team_id"] for row in events_b} != {202}
                or any("team_b" in row["event"] for row in events_a)
                or any("team_a" in row["event"] for row in events_b)):
            raise ProbeBlocked("synthetic_cross_team_query_leak")
        report["synthetic_team_predicates_qualified"] = True
        report["synthetic_event_rows"] = len(rows)
        report["teams_checked"] = [101, 202]
        report["queries_checked"] = 5
    except ProbeBlocked as exc:
        report["blocker"] = str(exc)
    except (OSError, ValueError) as exc:
        report["blocker"] = type(exc).__name__
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 1)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--clickhouse", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = qualify(args.repo, args.scratch, args.ref, clickhouse=args.clickhouse)
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print("Flind isolated ClickHouse:",
              "PASS" if result["synthetic_team_predicates_qualified"] else "BLOCKED")
    return 0 if result["synthetic_team_predicates_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
