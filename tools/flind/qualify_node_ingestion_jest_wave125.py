#!/usr/bin/env python3
"""Wave125: actual first-party Node WorkerIngest Jest suites with locked deps.

Run the four ORIGINAL Jest suites in a disposable full source checkout,
temporarily overlaying tracked current-main sources and restoring all files.
Requires an already-installed, free, frozen-lockfile local node_modules tree.
No npm installation, global config mutation, deployment or cloud calls.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
FULL = Path(os.environ.get("FLIND_NODE_JEST_FULL_CHECKOUT") or "/tmp/flind-wave76-frontend")
MIN_FREE = 10 * 1024**3
TESTS = (
    "src/ingestion/api/kafka-message-converter.test.ts",
    "src/ingestion/api/grpc-message-converter.test.ts",
    "src/ingestion/api/grpc-server.test.ts",
    "src/servers/grpc-stream-ingest-driver.test.ts",
)
OVERLAY = (
    "nodejs/src/ingestion/api/kafka-message-converter.ts",
    "nodejs/src/ingestion/api/kafka-message-converter.test.ts",
    "nodejs/src/ingestion/api/grpc-message-converter.ts",
    "nodejs/src/ingestion/api/grpc-message-converter.test.ts",
    "nodejs/src/ingestion/api/grpc-server.ts",
    "nodejs/src/ingestion/api/grpc-server.test.ts",
    "nodejs/src/ingestion/api/types.ts",
    "nodejs/src/servers/grpc-stream-ingest-driver.ts",
    "nodejs/src/servers/grpc-stream-ingest-driver.test.ts",
)
LOG = Path("/tmp/flind-wave125-four-original-node-jest.log")


def qualify() -> dict:
    output = {
        "original_node_jest_all_four_suites_qualified": False,
        "original_jest_suite_count": 0,
        "original_jest_test_count": 0,
        "temporary_checkout_sources_restored": False,
        "production_node_ingestion_worker_started": False,
        "production_clickhouse_persistence_qualified": False,
        "tenant_authenticated_api_qualified": False,
        "browser_dashboard_e2e_qualified": False,
        "release_qualified": False,
    }
    if shutil.disk_usage("/tmp").free < MIN_FREE:
        return {**output, "blocker": "At least 10GiB free required"}
    if not (FULL / "nodejs/jest.config.js").is_file() or not (
        FULL / "nodejs/node_modules/.bin/jest"
    ).is_file():
        return {**output, "blocker": "Frozen-lockfile local Node Jest dependency tree unavailable"}
    if not (FULL / ".git").exists():
        return {**output, "blocker": "Temporary full Git checkout unavailable"}

    old: dict[str, bytes | None] = {}
    for relative in OVERLAY:
        repo_source = ROOT / relative
        temp_source = FULL / relative
        if not repo_source.is_file():
            return {**output, "blocker": "Current main source missing: " + relative}
        try:
            check = subprocess.run(
                ["git", "-C", str(FULL), "status", "--porcelain", "--", relative],
                capture_output=True, text=True, timeout=12, check=True,
            )
        except (OSError, subprocess.SubprocessError):
            return {**output, "blocker": "Cannot verify scratch Git status"}
        if check.stdout.strip():
            return {**output, "blocker": "Scratch checkout has pre-existing changes: " + relative}
        old[relative] = temp_source.read_bytes() if temp_source.is_file() else None

    env = os.environ.copy()
    env.update({
        "CI": "true", "NODE_ENV": "test",
        "NODE_OPTIONS": "--max-old-space-size=1800",
        "JEST_JUNIT_OUTPUT_DIR": "",
    })
    cmd = [
        "./node_modules/.bin/jest", "--config", "jest.config.js",
        "--runInBand", "--forceExit", "--no-coverage", "--runTestsByPath",
        *TESTS,
    ]
    process = None
    limit = None
    try:
        for relative in OVERLAY:
            (FULL / relative).write_bytes((ROOT / relative).read_bytes())
        with LOG.open("wb") as file:
            process = subprocess.Popen(
                cmd, cwd=FULL / "nodejs", env=env,
                stdin=subprocess.DEVNULL, stdout=file, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            start = time.monotonic()
            while process.poll() is None:
                if shutil.disk_usage("/tmp").free < MIN_FREE:
                    limit = "10GiB disk reserve"
                    break
                if time.monotonic() - start > 100:
                    limit = "100-second Jest timeout"
                    break
                time.sleep(1)
            if limit and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)

        text = LOG.read_text(errors="replace")[-22000:]
        suites = re.search(r"Test Suites:\s+(\d+) passed,\s+(\d+) total", text)
        tests = re.search(r"Tests:\s+(\d+) passed,\s+(\d+) total", text)
        suite_count = int(suites.group(1)) if suites and suites.group(1) == suites.group(2) else 0
        test_count = int(tests.group(1)) if tests and tests.group(1) == tests.group(2) else 0
        output["original_jest_suite_count"] = suite_count
        output["original_jest_test_count"] = test_count
        output["original_node_jest_all_four_suites_qualified"] = (
            process.returncode == 0
            and limit is None
            and suite_count == len(TESTS)
            # Wave126 extends the actual gRPC suite with 10 protobuf uint64
            # protocol/budget boundaries; require all 53 real Jest cases.
            and test_count >= 53
            and all(f"PASS {name}" in text for name in TESTS)
        )
        output["native_jest_process_exit"] = process.returncode
        output["bounded_execution_sec"] = round(time.monotonic() - start, 1)
        if not output["original_node_jest_all_four_suites_qualified"]:
            output["blocker"] = limit or "Original Jest tests did not fully pass"
    except (OSError, ValueError, subprocess.SubprocessError):
        output["blocker"] = "Could not execute original Node Jest suites"
    finally:
        for relative, data in old.items():
            target = FULL / relative
            if data is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(data)
        output["temporary_checkout_sources_restored"] = all(
            (not (FULL / relative).exists()) if data is None
            else (FULL / relative).read_bytes() == data
            for relative, data in old.items()
        )
        output["original_node_jest_all_four_suites_qualified"] &= (
            output["temporary_checkout_sources_restored"]
        )
    return output


if __name__ == "__main__":
    result = qualify()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["original_node_jest_all_four_suites_qualified"] else 2)
