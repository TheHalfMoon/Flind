#!/usr/bin/env python3
"""Run one actual original Flind Rust Kafka/gRPC ledger test with private Kafka.

Pin old first-party source files to verified local Git blob objects; back up and
restore an existing disposable checkout. Cargo is strictly offline and limited
by wall-clock and a 3 GiB free disk reserve. This is a test gRPC worker, not
the production Node worker or release validation.
"""
from __future__ import annotations
import argparse
import hashlib
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
sys.path.insert(0, str(ROOT))
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import qualify as kafka_qualify

PINNED_COMMIT = "1905e9afb0f25f2685f042485b59f4c433403ffe"
FULL = Path("/private/tmp/flind-wave76-frontend")
TARGET = Path("/private/tmp/flind-wave110-rust-target")
ORIGINAL_ENDPOINT = 'const KAFKA_BROKERS: &str = "localhost:9092";'
CASE = "the_committed_offset_is_the_ledger_frontier"
CASES = (
    CASE,
    "a_partial_ack_redelivers_only_the_unfinished_messages",
    "consumer_crash_before_commit_redelivers_without_loss",
    "lost_ack_after_processing_replays_without_loss",
    "poison_batch_fails_safely_without_committing",
    "partial_acceptance_fails_the_batch_without_commit",
    "failing_worker_triggers_rerouting",
    "drainer_crash_mid_drain_replays_to_survivor_in_order",
    "nacking_worker_fences_worker_stream_and_reroutes_in_order",
)
FILES = (
    "rust/ingestion-consumer/src/consumer.rs",
    "rust/ingestion-consumer/src/rebalance.rs",
    "rust/ingestion-consumer/src/worker_registry.rs",
    "rust/ingestion-consumer/src/main.rs",
    "rust/ingestion-consumer/tests/e2e_integration_test.rs",
)
MIN_FREE_BYTES = 3 * 1024**3
MAX_COMPILE_SECONDS = 135


class RustBlocked(ValueError):
    pass


def offline_git(repo: Path, *args: str) -> bytes:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                              check=False, timeout=25, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RustBlocked("offline_git_unavailable") from exc
    if done.returncode or len(done.stdout) > 200_000:
        raise RustBlocked("offline_git_source_unavailable")
    return done.stdout


def verified_blob(repo: Path, relative: str) -> bytes:
    oid = offline_git(repo, "rev-parse", "HEAD:" + relative).decode().strip()
    if not re.fullmatch(r"[a-f0-9]{40}", oid):
        raise RustBlocked("unsafe_first_party_git_blob_id")
    raw = offline_git(repo, "show", "HEAD:" + relative)
    if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != oid:
        raise RustBlocked("first_party_git_blob_digest_mismatch")
    return raw


def source_ready(reference: Path, full: Path, bootstrap: str) -> bool:
    if not re.fullmatch(r"127\.0\.0\.1:[0-9]{4,5}", bootstrap):
        return False
    if reference.is_symlink() or full.is_symlink():
        return False
    if not reference.is_dir() or not full.is_dir() or reference.resolve() == full.resolve():
        return False
    if Path("/private/tmp").resolve() not in full.resolve().parents:
        return False
    if offline_git(reference, "rev-parse", "HEAD").decode().strip() != PINNED_COMMIT:
        return False
    if not (full / "rust/Cargo.toml").is_file() or not (full / "rust/Cargo.lock").is_file():
        return False
    if not (full / "proto/ingestion/worker/v1/worker.proto").is_file():
        return False
    if shutil.disk_usage("/private/tmp").free < MIN_FREE_BYTES:
        return False
    for name in FILES:
        if not (full / name).is_file() or (full / name).is_symlink():
            return False
        if offline_git(full, "status", "--porcelain", "--", name).strip():
            return False
    return True


def native_single_rust_test(bootstrap: str, _: Path, *, reference: Path, full: Path, case: str = CASE) -> dict:
    result: dict[str, object] = {
        "rust_original_kafka_grpc_ledger_test_pass": False,
        "rust_case": case,
        "original_git_blob_source_verified": False,
        "first_party_test_grpc_worker_qualified": False,
        "production_node_grpc_worker_qualified": False,
        "full_checkout_source_restored": False,
        "release_qualified": False,
    }
    restored: dict[str, bytes] = {}
    proc: subprocess.Popen | None = None
    started = time.monotonic()
    try:
        if case not in CASES:
            raise RustBlocked("unapproved_rust_integration_case")
        if not source_ready(reference, full, bootstrap):
            raise RustBlocked("source_or_disk_admission_failed")
        desired = {name: verified_blob(reference, name) for name in FILES}
        recorded = offline_git(full, "rev-parse", "HEAD:" + FILES[-1]).decode().strip()
        pinned_test_sha = offline_git(reference, "rev-parse", "HEAD:" + FILES[-1]).decode().strip()
        if recorded != pinned_test_sha:
            raise RustBlocked("original_rust_test_source_changed")
        original = desired[FILES[-1]]
        if original.count(ORIGINAL_ENDPOINT.encode()) != 1:
            raise RustBlocked("original_kafka_test_broker_constant_missing")
        restored = {name: (full / name).read_bytes() for name in FILES}
        result["original_git_blob_source_verified"] = True
        for name in FILES[:-1]:
            (full / name).write_bytes(desired[name])
        (full / FILES[-1]).write_bytes(
            original.replace(ORIGINAL_ENDPOINT.encode(),
                             f'const KAFKA_BROKERS: &str = "{bootstrap}";'.encode(), 1)
        )
        sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True,
                             timeout=8, check=True).stdout.decode().strip()
        env = {**os.environ, "SDKROOT": sdk,
               "CPLUS_INCLUDE_PATH": sdk + "/usr/include/c++/v1",
               "CARGO_NET_OFFLINE": "true", "CARGO_INCREMENTAL": "0",
               "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_BUILD_JOBS": "2",
               "CARGO_TARGET_DIR": str(TARGET), "RUST_LOG": "warn"}
        command = ["cargo", "test", "--locked", "--offline", "-p", "ingestion-consumer",
                   "--test", "e2e_integration_test", case, "--jobs", "2",
                   "--", "--exact", "--nocapture"]
        log = Path("/private/tmp/flind-wave184-rust-original-ledger.log")
        with log.open("wb") as stream:
            proc = subprocess.Popen(command, cwd=full / "rust", env=env,
                                    stdin=subprocess.DEVNULL, stdout=stream,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        stopper = None
        while proc.poll() is None:
            if shutil.disk_usage("/private/tmp").free < MIN_FREE_BYTES:
                stopper = "disk_reserve_below_3_gib"
                break
            if time.monotonic() - started >= MAX_COMPILE_SECONDS:
                stopper = "rust_original_test_deadline_reached"
                break
            time.sleep(1.5)
        if stopper is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
        last = log.read_text(errors="replace").splitlines()[-40:]
        match = (proc.returncode == 0
                 and any(f"test {case} ... ok" in line for line in last)
                 and any("test result: ok. 1 passed;" in line for line in last))
        result["first_party_test_grpc_worker_qualified"] = match
        result["rust_original_kafka_grpc_ledger_test_pass"] = match
        result["rust_test_exit_code"] = proc.returncode
        if not match:
            result["blocker"] = stopper or "original_rust_kafka_grpc_test_failed"
            result["safe_cargo_last_lines"] = [
                line[:180] for line in last[-8:]
                if "token" not in line.lower() and "password" not in line.lower()
            ]
    except (RustBlocked, OSError, subprocess.SubprocessError, ValueError) as exc:
        result["blocker"] = str(exc) if isinstance(exc, RustBlocked) else type(exc).__name__
    finally:
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        try:
            for name, saved in restored.items():
                (full / name).write_bytes(saved)
            result["full_checkout_source_restored"] = bool(restored) and all(
                (full / name).read_bytes() == saved for name, saved in restored.items()
            )
        except OSError:
            result["full_checkout_source_restored"] = False
        result["elapsed_seconds"] = round(time.monotonic() - started, 1)
    return result


def qualify(reference: Path, full: Path, kafka_home: Path, scratch: Path,
            clickhouse: str, *, case: str = CASE) -> dict:
    receipt = kafka_qualify(
        reference, kafka_home, scratch, clickhouse=clickhouse,
        on_broker_ready=lambda broker, child: native_single_rust_test(
            broker, child, reference=reference, full=full, case=case,
        ),
    )
    child = receipt.get("optional_private_kafka_probe") or {}
    passed = bool(receipt.get("local_clickhouse_relay_qualified")
                  and receipt.get("owned_kafka_process_stopped")
                  and receipt.get("owned_kafka_scratch_removed")
                  and child.get("rust_original_kafka_grpc_ledger_test_pass")
                  and child.get("full_checkout_source_restored"))
    return {
        "phase": "pinned-first-party-original-rust-kafka-test-grpc-worker",
        "pinned_source_commit": PINNED_COMMIT,
        "rust_case": case,
        "original_rust_kafka_grpc_test_pass": passed,
        "original_test_receipt": child,
        "owned_kafka_process_stopped": receipt.get("owned_kafka_process_stopped", False),
        "owned_kafka_scratch_removed": receipt.get("owned_kafka_scratch_removed", False),
        "real_node_ingestion_worker_qualified": False,
        "durable_clickhouse_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
        **({"blocker": child.get("blocker") or receipt.get("blocker") or "original_rust_test_unqualified"} if not passed else {}),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--full", type=Path, default=FULL)
    p.add_argument("--kafka-home", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--clickhouse", required=True)
    p.add_argument("--case", choices=CASES, default=CASE)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    r = qualify(a.reference, a.full, a.kafka_home, a.scratch, a.clickhouse, case=a.case)
    print(json.dumps(r, indent=2, sort_keys=True) if a.json else
          ("Flind Rust Kafka gRPC original test: " + ("PASS" if r["original_rust_kafka_grpc_test_pass"] else "BLOCKED")))
    return 0 if r["original_rust_kafka_grpc_test_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
