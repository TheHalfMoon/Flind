#!/usr/bin/env python3
"""Wave211: execute original Flind Rust gRPC transport tests, locally and offline.

Unlike the source-only Wave210 gate, this requires a real, successful
ingestion-consumer Rust integration test binary built from the current Git HEAD.
The gRPC worker in grpc_transport_test.rs is a first-party *test mock*.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.flind.qualify_rust_consumer_offline_wave210 import (
    metadata_check,
    source_attestation,
)

OWNER = ".flind-wave211-owner"
MARKER = "FLIND_WAVE211_OWNED_RUST_TARGET_V1\n"
TEST_TARGET = "grpc_transport_test"


def parse_test_result(output: str) -> tuple[int, int]:
    """Extract exactly the original Rust test binary's final result line."""
    matches = re.findall(
        r"test result:\s+(ok|FAILED)\.\s+(\d+) passed;\s+(\d+) failed;",
        output,
    )
    if len(matches) != 1:
        return 0, -1
    result, passed, failed = matches[0]
    if result != "ok":
        return int(passed), int(failed)
    return int(passed), int(failed)


def target_safely_owned(root: Path, target: Path) -> bool:
    """Never write into user Cargo targets or a non-marker-owned directory."""
    target = target.absolute()
    if target.is_symlink() or target.parent.resolve() != root.parent.resolve():
        return False
    if target.name != root.name + "-rust-target":
        return False
    if not target.exists():
        target.mkdir(mode=0o700)
        (target / OWNER).write_text(MARKER, encoding="utf8")
    return (target / OWNER).is_file() and (target / OWNER).read_text(encoding="utf8") == MARKER


def qualify(root: Path, target: Path, *, timeout_sec: int = 660) -> dict:
    root = root.resolve()
    base = {
        "phase": "wave211_original_flind_rust_grpc_transport_integration",
        "no_paid_compute": True,
        "network_downloads_disabled": True,
        "original_rust_grpc_test_binary_executed": False,
        "original_rust_grpc_transport_qualified": False,
        "original_rust_kafka_consumer_broker_qualified": False,
        "original_node_joined_pipeline_qualified": False,
        "durable_clickhouse_qualified": False,
        "django_tenant_auth_qualified": False,
        "release_qualified": False,
    }
    try:
        provenance = source_attestation(root)
        metadata = metadata_check(root)
        if not all((
            provenance["tracked_first_party_sources"],
            provenance["tracked_sources_match_head"],
            metadata["cargo_offline_locked_metadata_pass"],
        )):
            return {**base, **provenance, **metadata,
                    "blocker": "unattested_first_party_source_or_cargo_metadata"}
        if not target_safely_owned(root, target):
            return {**base, **provenance, **metadata, "blocker": "unowned_cargo_target"}

        env = {**os.environ,
            "CARGO_NET_OFFLINE": "true", "CARGO_BUILD_JOBS": "2",
            "CARGO_INCREMENTAL": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
            "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_TARGET_DIR": str(target),
            "SQLX_OFFLINE": "true",
        }
        log = target / "wave211-cargo-grpc-test.log"
        started = time.monotonic()
        stopped_reason = None
        with log.open("wb") as output:
            process = subprocess.Popen(
                ["cargo", "test", "--offline", "--locked", "-p", "ingestion-consumer",
                 "--test", TEST_TARGET, "-j", "2", "--", "--test-threads=2"],
                cwd=root / "rust", env=env, stdin=subprocess.DEVNULL,
                stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
            )
            while process.poll() is None:
                if time.monotonic() - started > timeout_sec:
                    stopped_reason = "bounded_native_test_timeout"
                    break
                if shutil.disk_usage(target).free < 12 * 1024**3:
                    stopped_reason = "12GiB_free_disk_reserve"
                    break
                time.sleep(1)
            if stopped_reason and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=7)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)

        text = log.read_text(encoding="utf8", errors="replace")
        passed, failed = parse_test_result(text)
        actual_binary_executed = bool(re.search(r"running \d+ tests", text))
        qualified = all((
            process.returncode == 0, stopped_reason is None,
            actual_binary_executed, passed >= 15, failed == 0,
        ))
        return {
            **base, **provenance, **metadata,
            "original_rust_grpc_test_binary_executed": actual_binary_executed,
            "original_rust_grpc_transport_qualified": qualified,
            "native_rust_test_passed": passed,
            "native_rust_test_failed": failed,
            "native_test_exit_code": process.returncode,
            "native_test_elapsed_sec": round(time.monotonic() - started, 1),
            "owned_local_test_log": str(log),
            **({"blocker": stopped_reason or "native_rust_grpc_test_failed"}
               if not qualified else {}),
        }
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {**base, "blocker": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--target", type=Path,
                        default=ROOT.parent / (ROOT.name + "-rust-target"))
    parser.add_argument("--timeout-sec", type=int, default=660)
    args = parser.parse_args()
    if not 30 <= args.timeout_sec <= 1800:
        parser.error("--timeout-sec must be within [30, 1800]")
    report = qualify(args.repo, args.target, timeout_sec=args.timeout_sec)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["original_rust_grpc_transport_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
