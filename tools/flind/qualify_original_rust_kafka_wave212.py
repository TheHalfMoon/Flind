#!/usr/bin/env python3
"""Wave212: prove original Rust ingestion consumer replay/commit with real Kafka.

Runs three original first-party Rust integration tests against an isolated
Kafka 4.3.1 loopback KRaft broker with synthetic messages only. The worker in
these tests is a first-party gRPC test server, NOT the production Node worker.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.flind import qualify_ephemeral_kafka_wave84 as kafka
from tools.flind.qualify_rust_consumer_offline_wave210 import (
    metadata_check, source_attestation,
)

TESTS = (
    "the_committed_offset_is_the_ledger_frontier",
    "a_partial_ack_redelivers_only_the_unfinished_messages",
    "consumer_crash_before_commit_redelivers_without_loss",
)
SOURCE = "rust/ingestion-consumer/tests/e2e_integration_test.rs"
MARKER = "FLIND_WAVE212_LOCAL_RUNTIME_V1\n"


def verify_runtime(runtime: Path) -> bool:
    if runtime.is_symlink() or not runtime.is_dir():
        return False
    # Windows directory junctions are reparse points, not symlinks, and can
    # redirect an apparently owner-marked directory to a foreign location.
    if (getattr(runtime.lstat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
        return False
    owner = runtime / ".flind-wave212-owner"
    if not owner.is_file() or owner.read_text(encoding="utf8") != MARKER:
        return False
    archive = runtime / "kafka.tgz"
    checksum = runtime / "kafka.sha512"
    if not archive.is_file() or not checksum.is_file():
        return False
    text = checksum.read_text(encoding="utf8")
    if ":" not in text:
        return False
    expected = "".join(text.split(":", 1)[1].split()).lower()
    if not re.fullmatch(r"[0-9a-f]{128}", expected):
        return False
    digest = hashlib.sha512()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == expected and (
        runtime / "kafka/bin/kafka-server-start.sh"
    ).is_file()


def e2e_source_matches_head(root: Path) -> bool:
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", SOURCE],
        capture_output=True, timeout=15, check=False,
    )
    clean = subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", SOURCE],
        capture_output=True, timeout=30, check=False,
    )
    return tracked.returncode == 0 and clean.returncode == 0


def select_loopback_kafka_ports() -> tuple[int, int]:
    with socket.socket() as service:
        service.bind(("127.0.0.1", 9092))
        service.listen()
    for _ in range(5):
        _, controller = kafka.loopback_ports_original()
        if controller not in (9092, 9093):
            return 9092, controller
    raise ValueError("No safe isolated controller port")


def broker_cleanup_verified(
    private_tmp: Path, *, port: int = 9092, timeout_seconds: float = 10.0
) -> bool:
    """Fail closed until no private files or live Kafka TCP listener remain.

    Binding a recently closed server port can fail because of TIME_WAIT even
    though the listener is gone; require a genuine connection refusal instead.
    """
    deadline = time.monotonic() + timeout_seconds
    while True:
        if not any(private_tmp.glob("flind-kafka-*")):
            with socket.socket() as probe:
                probe.settimeout(0.25)
                if probe.connect_ex(("127.0.0.1", port)) == errno.ECONNREFUSED:
                    return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))


def run_original_tests(root: Path, target: Path) -> dict:
    owner = target / ".flind-wave211-owner"
    if (target.is_symlink() or not owner.is_file()
            or owner.read_text(encoding="utf8") != "FLIND_WAVE211_OWNED_RUST_TARGET_V1\n"):
        return {"passed": False, "blocker": "missing marker-owned native Rust target"}
    env = {**os.environ,
           "CARGO_NET_OFFLINE": "true",
           "CARGO_INCREMENTAL": "0",
           "CARGO_BUILD_JOBS": "2",
           "CARGO_PROFILE_TEST_DEBUG": "0",
           "CARGO_PROFILE_DEV_DEBUG": "0",
           "CARGO_TARGET_DIR": str(target),
           "SQLX_OFFLINE": "true",
           }
    outcomes = []
    for case in TESTS:
        result = subprocess.run(
            ["cargo", "test", "--offline", "--locked", "-p", "ingestion-consumer",
             "--test", "e2e_integration_test", "-j", "2", case, "--",
             "--test-threads=1"],
            cwd=root / "rust", env=env, capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=300, check=False,
        )
        summary = re.findall(
            r"test result:\s+(ok|FAILED)\.\s+(\d+) passed;\s+(\d+) failed;",
            result.stdout,
        )
        ok = (
            result.returncode == 0 and len(summary) == 1
            and summary[0] == ("ok", "1", "0")
            and bool(re.search(r"(?m)^running 1 test\s*$", result.stdout))
            and case in result.stdout
        )
        outcomes.append({"test": case, "passed": ok, "native_exit": result.returncode,
                         "actual_native_case_executed": bool(summary)})
        if not ok:
            break
    return {"passed": len(outcomes) == len(TESTS) and all(x["passed"] for x in outcomes),
            "cases": outcomes}


def qualify(root: Path, runtime: Path, target: Path) -> dict:
    base = {
        "phase": "wave212_original_rust_consumer_real_kafka_offset_acks",
        "original_rust_kafka_e2e_qualified": False,
        "original_rust_test_cases_passed": 0,
        "real_isolated_kafka_431_qualified": False,
        "production_node_joined_pipeline_qualified": False,
        "durable_clickhouse_qualified": False,
        "django_tenant_auth_qualified": False,
        "release_qualified": False,
    }
    try:
        root = root.resolve()
        provenance = source_attestation(root)
        meta = metadata_check(root)
        if not (provenance["tracked_sources_match_head"]
                and provenance["tracked_first_party_sources"]
                and meta["cargo_offline_locked_metadata_pass"]
                and e2e_source_matches_head(root)):
            return {**base, "blocker": "unattested Rust E2E source or metadata"}
        if not verify_runtime(runtime):
            return {**base, "blocker": "missing or unverified owned Kafka runtime"}
        if shutil.disk_usage(root).free < 12 * 1024**3:
            return {**base, "blocker": "12 GiB free disk reserve"}
        if not (os.environ.get("JAVA_HOME") and os.environ.get("PROTOC")):
            return {**base, "blocker": "isolated JAVA_HOME and PROTOC must be provided"}
        # Pin broker to 9092: the ORIGINAL Rust E2E fixture uses this
        # local address. Never bind another user's port or modify a host broker.
        private_tmp = runtime / "tmp"
        if private_tmp.is_symlink():
            return {**base, "blocker": "unsafe temporary Kafka storage"}
        private_tmp.mkdir(exist_ok=True)
        original = kafka.loopback_ports
        kafka.loopback_ports_original = original
        kafka.loopback_ports = select_loopback_kafka_ports
        try:
            # WSL's /tmp may be a small tmpfs. Put private Kafka data on the
            # large, owned Linux volume, not global /tmp or a host broker.
            with patch.object(kafka, "available_disk_gib",
                              lambda: shutil.disk_usage(runtime).free / (1024**3)), \
                 patch.object(tempfile, "tempdir", str(private_tmp)):
                receipt = kafka.qualify_kafka(
                    runtime / "kafka",
                    on_broker_ready=lambda bootstrap: (
                        run_original_tests(root, target) if bootstrap == "127.0.0.1:9092"
                        else {"passed": False, "blocker": "nonlocal Kafka bootstrap"}
                    ),
                )
        finally:
            kafka.loopback_ports = original
            del kafka.loopback_ports_original
        # The original Wave84 Kafka helper returns the user-supplied
        # on_broker_ready receipt under native_capture_relay, not the
        # similarly named key used by other legacy qualification wrappers.
        native = receipt.get("native_capture_relay") or {}
        cases = native.get("cases") or []
        cleaned = broker_cleanup_verified(private_tmp)
        passed = all((
            receipt.get("isolated_kafka_passed") is True,
            native.get("passed") is True,
            len(cases) == 3,
            all(c.get("passed") is True for c in cases),
            cleaned,
        ))
        return {
            **base,
            "source_head_sha": provenance["head_sha"],
            "real_isolated_kafka_431_qualified": receipt.get("isolated_kafka_passed") is True,
            "original_rust_test_cases_passed": sum(c.get("passed") is True for c in cases),
            "original_rust_kafka_e2e_qualified": passed,
            "native_test_results": cases,
            "private_kafka_cleanup_qualified": cleaned,
            **({"blocker": native.get("blocker") or receipt.get("blocker") or "native tests failed"}
               if not passed else {}),
        }
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        return {**base, "blocker": type(exc).__name__}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--runtime", type=Path,
                        default=Path.home() / "work" / "Flind-wave212-runtime")
    parser.add_argument("--rust-target", type=Path,
                        default=Path.home() / "work" / "Flind-wave211-rust-target")
    args = parser.parse_args()
    evidence = qualify(args.repo, args.runtime, args.rust_target)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    raise SystemExit(0 if evidence["original_rust_kafka_e2e_qualified"] else 2)
