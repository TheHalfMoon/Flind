#!/usr/bin/env python3
"""Wave128 real isolated ClickHouse HTTP readback via actual Node helper origin.

Uses a private loopback, memory-bounded temporary CH25.12.7.21 process.
Node executes the SAME dependency-free endpoint selector imported by the
original Clickhouse test helper (which requires unbuilt native re2).
No user database reset, no default 8123, no cloud or paid resources.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from tools.flind.qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http

ROOT = Path(__file__).resolve().parents[2]
DB = "flind_test_isolatedwave128q9a1"
BINARY = Path("/tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64")
NODE_TEST = ROOT / "tools/flind/test_node_clickhouse_private_http_wave128.mjs"
MIN_FREE = 10 * 1024**3


def active_server_probe(port: int) -> dict:
    receipt = {
        "actual_node_endpoint_helper_exercised": False,
        "node_reached_actual_clickhouse": False,
        "real_clickhouse_sql_readback": False,
        "original_full_clickhouse_helper_runtime_loaded": False,
        "release_qualified": False,
    }
    if port == 8123 or not 1025 <= port <= 65535:
        return {**receipt, "blocker": "Private ClickHouse non-default port absent"}
    if shutil.disk_usage("/tmp").free < MIN_FREE:
        return {**receipt, "blocker": "Disk below safety reserve"}

    try:
        sql_http(port, f"CREATE DATABASE {DB}")
        sql_http(port, f"CREATE TABLE {DB}.flind_private_probe (value UInt32) ENGINE = Memory")
        sql_http(port, f"INSERT INTO {DB}.flind_private_probe VALUES (10),(20),(30)")
    except (OSError, ValueError):
        return {**receipt, "blocker": "Private real ClickHouse fixture creation failed"}

    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C",
        "FLIND_W128_CLICKHOUSE_HTTP_PORT": str(port),
        "FLIND_W128_CLICKHOUSE_DATABASE": DB,
    }
    cmd = ["node", "--no-warnings", "--experimental-strip-types", str(NODE_TEST)]
    try:
        completed = subprocess.run(
            cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return {**receipt, "blocker": "Actual Node/ClickHouse native readback not executed"}
    receipt["native_node_exit"] = completed.returncode
    try:
        observed = json.loads(completed.stdout)
    except (ValueError, TypeError):
        observed = {}
    passed = (
        completed.returncode == 0
        and observed.get("first_party_clickhouse_origin_exercised") is True
        and observed.get("isolated_real_clickhouse_sql_readback") is True
        and observed.get("observed_rows") == 3
        and observed.get("observed_sum") == 60
        and observed.get("release_qualified") is False
    )
    receipt["actual_node_endpoint_helper_exercised"] = passed
    receipt["node_reached_actual_clickhouse"] = passed
    receipt["real_clickhouse_sql_readback"] = passed
    if not passed:
        receipt["blocker"] = "First-party Node HTTP origin real ClickHouse readback failed"
        receipt["native_node_stderr"] = completed.stderr[-1000:]
    return receipt


def qualify() -> dict:
    result = {
        "first_party_node_clickhouse_port_real_sql_qualified": False,
        "actual_private_clickhouse_started": False,
        "actual_node_test_executed": False,
        "private_server_process_cleanup_completed": False,
        "full_clickhouse_helper_import_qualified": False,
        "production_rust_node_clickhouse_e2e_qualified": False,
        "release_qualified": False,
    }
    if not BINARY.is_file() or not NODE_TEST.is_file():
        return {**result, "blocker": "Native binary or Node probe missing"}
    actual = isolated_clickhouse(binary=str(BINARY), on_ready=active_server_probe)
    child = actual.get("event_readback") or {}
    passed = (
        actual.get("isolated_clickhouse_passed") is True
        and child.get("real_clickhouse_sql_readback") is True
        and child.get("actual_node_endpoint_helper_exercised") is True
    )
    # Original helper owns the server's subprocess in a try/finally, which
    # terminates the process after callback, including error exits.
    return {
        **result,
        "first_party_node_clickhouse_port_real_sql_qualified": passed,
        "actual_private_clickhouse_started": actual.get("isolated_clickhouse_passed") is True,
        "actual_node_test_executed": child.get("native_node_exit") == 0,
        # isolated_clickhouse waits for the owned child to exit in finally
        # before returning. No process ID/secret from the child is surfaced.
        "private_server_process_cleanup_completed": bool(actual),
        "node_http_receipt": child,
        **({"blocker": child.get("blocker") or actual.get("reason") or "Live qualification failed"}
           if not passed else {}),
    }


if __name__ == "__main__":
    receipt = qualify()
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["first_party_node_clickhouse_port_real_sql_qualified"] else 2)
