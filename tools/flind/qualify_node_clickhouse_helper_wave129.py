#!/usr/bin/env python3
"""Wave129: original first-party Node Clickhouse helper ↔ isolated real CH.

Runs the ACTUAL Clickhouse.create()/query() class via first-party Jest under
Node24 with private scratch-only re2 native dependency. No production service,
shared 8123, external database, paid cloud or user data.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from tools.flind.qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http

ROOT = Path(__file__).resolve().parents[2]
FULL = Path("/tmp/flind-wave76-frontend")
NODE24 = Path("/opt/homebrew/Cellar/node@24/24.15.0/bin")
BINARY = Path("/tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64")
DB = "flind_test_nativehelperwave129q"
FILES = (
    "nodejs/tests/helpers/clickhouse.ts",
    "nodejs/tests/helpers/clickhouse-http-endpoint.ts",
    "nodejs/tests/helpers/clickhouse-real-port-wave129.test.ts",
)
MIN_DISK = 10 * 1024**3


def on_clickhouse_ready(port: int) -> dict:
    receipt = {
        "actual_first_party_clickhouse_helper_jest_passed": False,
        "actual_node24_native_re2_loaded": False,
        "real_clickhouse_http_sql_query": False,
        "scratch_source_restored": False,
        "production_node_worker_started": False,
        "release_qualified": False,
    }
    if port == 8123 or shutil.disk_usage("/tmp").free < MIN_DISK:
        return {**receipt, "blocker": "Nondefault CH port or disk reserve unavailable"}
    if not (FULL / "nodejs/node_modules/.bin/jest").is_file():
        return {**receipt, "blocker": "Original Node Jest dependencies missing"}
    re2 = FULL / "node_modules/.pnpm/re2@1.22.1_supports-color@10.2.2/node_modules/re2/build/Release/re2.node"
    if not re2.is_file() or not (NODE24 / "node").is_file():
        return {**receipt, "blocker": "Node24 isolated native RE2 binding unavailable"}
    previous: dict[str, bytes | None] = {}
    for file in FILES:
        check = subprocess.run(
            ["git", "-C", str(FULL), "status", "--porcelain", "--", file],
            capture_output=True, text=True, timeout=13, check=True,
        )
        if check.stdout.strip():
            return {**receipt, "blocker": "Previous scratch worktree file edits found"}
        previous[file] = (FULL / file).read_bytes() if (FULL / file).is_file() else None
    log = Path("/tmp/flind-wave129-first-party-clickhouse-jest.log")
    try:
        sql_http(port, f"CREATE DATABASE {DB}")
        sql_http(port, f"CREATE TABLE {DB}.flind_private_probe (value UInt32) ENGINE = Memory")
        sql_http(port, f"INSERT INTO {DB}.flind_private_probe VALUES (10),(20),(30)")
        for file in FILES:
            (FULL / file).write_bytes((ROOT / file).read_bytes())
        # Keep unrelated project/cloud tokens and ambient database endpoints
        # out of the native Jest subprocess, just as the service-E2E runner does.
        env = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "TMPDIR", "LANG", "TZ")
            if key in os.environ
        }
        env.update({
            "PATH": str(NODE24) + ":" + env.get("PATH", "/usr/bin:/bin"),
            "NODE_ENV": "test",
            "CI": "true",
            "NODE_OPTIONS": "--max-old-space-size=1600",
            "CLICKHOUSE_HOST": "127.0.0.1",
            "CLICKHOUSE_HTTP_PORT": str(port),
            "CLICKHOUSE_DATABASE": DB,
            "FLIND_W129_CLICKHOUSE_HTTP_PORT": str(port),
            "FLIND_W129_CLICKHOUSE_DATABASE": DB,
            "OTEL_SDK_DISABLED": "true",
        })
        cmd = [
            "./node_modules/.bin/jest", "--config", "jest.config.js",
            "--runInBand", "--forceExit", "--no-coverage", "--runTestsByPath",
            "tests/helpers/clickhouse-real-port-wave129.test.ts",
        ]
        with log.open("wb") as out:
            child = subprocess.Popen(
                cmd, cwd=FULL / "nodejs", env=env,
                stdin=subprocess.DEVNULL,
                stdout=out, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            started = time.monotonic()
            timeout_reason = None
            while child.poll() is None:
                if shutil.disk_usage("/tmp").free < MIN_DISK:
                    timeout_reason = "10GiB disk reserve"
                    break
                if time.monotonic() - started > 55:
                    timeout_reason = "bounded 55sec local Jest run"
                    break
                time.sleep(1)
            if timeout_reason and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=5)
        stdout = log.read_text(errors="replace")[-18000:]
        success = (
            child.returncode == 0
            and timeout_reason is None
            and "Test Suites: 1 passed, 1 total" in stdout
            and "Tests:       1 passed, 1 total" in stdout
        )
        receipt["actual_first_party_clickhouse_helper_jest_passed"] = success
        receipt["actual_node24_native_re2_loaded"] = success
        receipt["real_clickhouse_http_sql_query"] = success
        receipt["native_jest_exit_code"] = child.returncode
        if not success:
            receipt["blocker"] = timeout_reason or "Actual original helper Jest failed"
            receipt["diagnostics"] = [line[:200] for line in stdout.splitlines()[-15:]]
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        receipt["blocker"] = "Actual Node helper or ClickHouse SQL could not run"
        receipt["error_type"] = type(exc).__name__
    finally:
        for file, data in previous.items():
            if data is None:
                (FULL / file).unlink(missing_ok=True)
            else:
                (FULL / file).write_bytes(data)
        receipt["scratch_source_restored"] = all(
            not (FULL / file).exists() if data is None else
            (FULL / file).read_bytes() == data
            for file, data in previous.items()
        )
        receipt["actual_first_party_clickhouse_helper_jest_passed"] &= receipt["scratch_source_restored"]
    return receipt


def qualify() -> dict:
    actual = isolated_clickhouse(binary=str(BINARY), on_ready=on_clickhouse_ready)
    child = actual.get("event_readback") or {}
    passed = (
        actual.get("isolated_clickhouse_passed") is True
        and child.get("actual_first_party_clickhouse_helper_jest_passed") is True
        and child.get("scratch_source_restored") is True
    )
    return {
        "first_party_node24_clickhouse_helper_real_sql_qualified": passed,
        "isolated_real_clickhouse_started": actual.get("isolated_clickhouse_passed") is True,
        "real_original_helper_receipt": child,
        "full_production_node_worker_started": False,
        "production_rust_node_clickhouse_ingestion_qualified": False,
        "release_qualified": False,
        **({"blocker": child.get("blocker") or actual.get("reason") or "Native test blocked"}
           if not passed else {}),
    }


if __name__ == "__main__":
    result = qualify()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["first_party_node24_clickhouse_helper_real_sql_qualified"] else 2)
