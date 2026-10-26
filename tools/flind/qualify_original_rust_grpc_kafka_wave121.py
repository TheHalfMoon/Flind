#!/usr/bin/env python3
"""Wave121 — run genuine first-party Rust ingestion consumer gRPC/Kafka E2E.

Runs three existing Rust integration tests (real Kafka4.3.1 broker, real
Rust Kafka consumer, first-party *test* gRPC WorkerIngest server, offset-ACK
frontier assertions). No real Node ingestion worker or product ClickHouse.
All Cargo compilation is offline, and temp worktree files are restored.
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

from tools.flind.qualify_ephemeral_kafka_wave84 import qualify_kafka
from tools.flind.qualify_native_capture_kafka_wave113 import DEFAULT_HOME

ROOT = Path(__file__).resolve().parents[2]
FULL = Path(os.environ.get("FLIND_W121_FULL_CHECKOUT") or "/tmp/flind-wave76-frontend")
TARGET = Path(os.environ.get("FLIND_W121_CARGO_TARGET") or "/tmp/flind-wave110-rust-target")
TESTS = (
    "the_committed_offset_is_the_ledger_frontier",
    "a_partial_ack_redelivers_only_the_unfinished_messages",
    "consumer_crash_before_commit_redelivers_without_loss",
)
# Wave122 expands only the approved original test-name allowlist; the
# Wave121 default still runs the original three and remains backwards-safe.
FAILURE_CASES = (
    "lost_ack_after_processing_replays_without_loss",
    "poison_batch_fails_safely_without_committing",
    "partial_acceptance_fails_the_batch_without_commit",
)
RECOVERY_CASES = (
    "failing_worker_triggers_rerouting",
    "drainer_crash_mid_drain_replays_to_survivor_in_order",
    "nacking_worker_fences_worker_stream_and_reroutes_in_order",
)
APPROVED_CASES = (*TESTS, *FAILURE_CASES, *RECOVERY_CASES)
ORIGINAL_ENDPOINT = 'const KAFKA_BROKERS: &str = "localhost:9092";'
PRODUCT_SOURCES = (
    "rust/ingestion-consumer/src/consumer.rs",
    "rust/ingestion-consumer/src/rebalance.rs",
    "rust/ingestion-consumer/src/worker_registry.rs",
    "rust/ingestion-consumer/src/main.rs",
)
TEST_SOURCE = "rust/ingestion-consumer/tests/e2e_integration_test.rs"
MIN_DISK = 10 * 1024**3


def git(repo: Path, *args: str) -> str:
    run = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, timeout=13, check=False,
    )
    if run.returncode:
        raise ValueError("Git source verification failed")
    return run.stdout.strip()


def smoke(bootstrap: str, *, tests: tuple[str, ...] = TESTS) -> dict:
    result = {
        "first_party_rust_grpc_kafka_e2e": False,
        "original_in_tree_e2e_test_executed": False,
        "real_rust_kafka_offset_frontier_assertions": False,
        "real_kafka_broker_private": bootstrap.startswith("127.0.0.1:"),
        "full_checkout_original_source_restored": False,
        "production_node_worker_qualified": False,
        "product_clickhouse_schema_qualified": False,
        "tenant_query_api_qualified": False,
        "browser_dashboard_qualified": False,
        "release_qualified": False,
    }
    if not re.fullmatch(r"127\.0\.0\.1:\d{4,5}", bootstrap):
        return {**result, "blocker": "Kafka broker not loopback"}
    # Fixed original test-name allowlist: no command argument injection or
    # accidental execution of broad/long-running integration suites.
    if not tests or len(tests) > len(TESTS) or len(set(tests)) != len(tests) or any(
        name not in APPROVED_CASES for name in tests
    ):
        return {**result, "blocker": "Unapproved Rust integration test selection"}
    if shutil.disk_usage("/tmp").free < MIN_DISK:
        return {**result, "blocker": "10GiB disk reserve required"}
    if not (FULL / "rust/Cargo.toml").is_file() or not (FULL / TEST_SOURCE).is_file():
        return {**result, "blocker": "Original full Rust integration test checkout absent"}
    if not (FULL / "proto/ingestion/worker/v1/worker.proto").is_file():
        return {**result, "blocker": "Original worker protobuf source absent"}
    try:
        if git(FULL, "rev-parse", "HEAD:" + TEST_SOURCE) != git(ROOT, "rev-parse", "HEAD:" + TEST_SOURCE):
            return {**result, "blocker": "Existing Rust e2e test source not identical to main"}
        for relative in (*PRODUCT_SOURCES, TEST_SOURCE):
            if git(FULL, "status", "--porcelain", "--", relative):
                return {**result, "blocker": "Temporary full checkout contains prior edits"}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {**result, "blocker": "Unable to verify test source provenance"}

    original = {path: (FULL / path).read_bytes() for path in (*PRODUCT_SOURCES, TEST_SOURCE)}
    source = original[TEST_SOURCE].decode("utf8")
    if source.count(ORIGINAL_ENDPOINT) != 1:
        return {**result, "blocker": "Expected exact first-party Kafka test broker constant missing"}
    try:
        sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True,
                             text=True, timeout=9, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {**result, "blocker": "Native macOS SDK unavailable"}

    env = os.environ.copy()
    env.update({
        "SDKROOT": sdk,
        "CPLUS_INCLUDE_PATH": sdk + "/usr/include/c++/v1",
        "CARGO_NET_OFFLINE": "true",
        "CARGO_INCREMENTAL": "0",
        "CARGO_PROFILE_DEV_DEBUG": "0",
        "CARGO_BUILD_JOBS": "2",
        "CARGO_TARGET_DIR": str(TARGET),
        "RUST_LOG": "warn",
    })
    log = Path("/tmp/flind-wave121-original-rust-e2e.log")
    process = None
    stopped_for_resource = None
    completed: dict[str, bool] = {}
    try:
        for relative in PRODUCT_SOURCES:
            (FULL / relative).write_bytes((ROOT / relative).read_bytes())
        (FULL / TEST_SOURCE).write_text(
            source.replace(ORIGINAL_ENDPOINT,
                           f'const KAFKA_BROKERS: &str = "{bootstrap}";', 1),
            encoding="utf8",
        )
        started = time.monotonic()
        for case in tests:
            cmd = [
                "cargo", "test", "--locked", "--offline", "-p", "ingestion-consumer",
                "--test", "e2e_integration_test", case, "--jobs", "2",
                "--", "--exact", "--nocapture",
            ]
            with log.open("wb") as output:
                process = subprocess.Popen(
                    cmd, cwd=FULL / "rust", env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                )
                while process.poll() is None:
                    if shutil.disk_usage("/tmp").free < MIN_DISK:
                        stopped_for_resource = "minimum disk reserve"
                        break
                    if time.monotonic() - started > 130:
                        stopped_for_resource = "bounded three-test timeout"
                        break
                    time.sleep(2)
                if stopped_for_resource and process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=6)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait(timeout=7)
            last = log.read_text(errors="replace").splitlines()[-45:]
            passed = (
                process.returncode == 0
                and any(f"test {case} ... ok" in line for line in last)
                and any("test result: ok. 1 passed;" in line for line in last)
                and stopped_for_resource is None
            )
            completed[case] = passed
            if not passed:
                result["blocker"] = stopped_for_resource or f"Original Rust E2E failed: {case}"
                result["synthetic_test_last_output"] = [line[:215] for line in last[-9:]]
                break
        all_passed = len(completed) == len(tests) and all(completed.values())
        result["first_party_rust_grpc_kafka_e2e"] = all_passed
        result["original_in_tree_e2e_test_executed"] = bool(completed)
        result["real_rust_kafka_offset_frontier_assertions"] = all_passed
        result["actual_first_party_test_results"] = completed
        result["native_rust_test_exit"] = process.returncode if process else None
        result["bounded_three_test_runtime_sec"] = round(time.monotonic() - started, 1)
    except (OSError, ValueError, subprocess.SubprocessError):
        result["blocker"] = "Could not execute original offline Rust Kafka/gRPC E2E"
    finally:
        for relative, data in original.items():
            (FULL / relative).write_bytes(data)
        result["full_checkout_original_source_restored"] = all(
            (FULL / relative).read_bytes() == data
            for relative, data in original.items()
        )
    return result


def qualify(*, tests: tuple[str, ...] = TESTS) -> dict:
    broker = qualify_kafka(DEFAULT_HOME, on_broker_ready=lambda addr: smoke(addr, tests=tests))
    native = broker.get("native_capture_relay") or {}
    passed = (
        broker.get("isolated_kafka_passed") is True
        and native.get("first_party_rust_grpc_kafka_e2e") is True
        and native.get("full_checkout_original_source_restored") is True
    )
    return {
        "native_rust_kafka_grpc_offset_frontier_qualified": passed,
        "isolated_real_kafka_431": broker.get("isolated_kafka_passed") is True,
        "native_test_receipt": native,
        "production_nodejs_ingestion_worker_qualified": False,
        "durable_product_clickhouse_qualified": False,
        "authenticated_product_query_qualified": False,
        "release_qualified": False,
        **({"blocker": native.get("blocker") or broker.get("blocker") or "E2E unavailable"}
           if not passed else {}),
    }


if __name__ == "__main__":
    receipt = qualify()
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["native_rust_kafka_grpc_offset_frontier_qualified"] else 2)
