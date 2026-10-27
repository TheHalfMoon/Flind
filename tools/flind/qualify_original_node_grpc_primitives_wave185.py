#!/usr/bin/env python3
"""Offline source-attested Node gRPC/Kafka primitive regression probe.

Verify original tracked first-party TS module Git blobs before invoking
the no-external-package Node 26 probe. Fail closed; never promote worker or
release qualification from unit-level serialization/security assertions.
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

MODULES = (
    "nodejs/src/ingestion/api/grpc-message-converter.ts",
    "nodejs/src/ingestion/api/kafka-message-converter.ts",
    "nodejs/src/ingestion/api/grpc-error-sanitizer.ts",
)
RUNNER = "tools/flind/verify_original_grpc_boundary_wave185.mjs"
TEST_COUNT = 32
MAX_SOURCE_BYTES = 20000
MAX_OUTPUT_BYTES = 3000


class Blocked(ValueError):
    pass


def _blob(reference: Path, relative: str) -> tuple[str, bytes]:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    try:
        listing = subprocess.run(["git", "-C", str(reference), "ls-tree", "HEAD", "--", relative],
                                 capture_output=True, timeout=12, env=env, check=False)
        if listing.returncode:
            raise Blocked("git_source_lookup_failed")
        fields = listing.stdout.decode("ascii").strip().split()
        if len(fields) != 4 or fields[:2] != ["100644", "blob"]:
            raise Blocked("missing_tracked_first_party_typescript_module")
        oid = fields[2]
        if not re.fullmatch(r"[0-9a-f]{40}", oid):
            raise Blocked("unexpected_git_blob_oid")
        raw = subprocess.run(["git", "-C", str(reference), "show", "HEAD:" + relative],
                             capture_output=True, timeout=12, env=env, check=False)
        if raw.returncode or len(raw.stdout) > MAX_SOURCE_BYTES:
            raise Blocked("original_module_blob_unavailable")
        digest = hashlib.sha1(f"blob {len(raw.stdout)}\0".encode() + raw.stdout).hexdigest()
        if digest != oid:
            raise Blocked("original_module_git_digest_mismatch")
        return oid, raw.stdout
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise Blocked("original_module_offline_git_unavailable") from exc


def verified_modules(reference: Path, runner_root: Path) -> dict[str, str]:
    if reference.is_symlink() or not reference.is_dir() or runner_root.is_symlink() or not runner_root.is_dir():
        raise Blocked("source_or_runner_root_refused")
    hashes: dict[str, str] = {}
    for relative in MODULES:
        candidate = runner_root / relative
        if not candidate.is_file() or candidate.is_symlink():
            raise Blocked("unavailable_or_symlinked_original_node_module")
        oid, reference_bytes = _blob(reference, relative)
        if candidate.read_bytes() != reference_bytes:
            raise Blocked("original_node_source_drift")
        hashes[relative] = oid
    script = runner_root / RUNNER
    if not script.is_file() or script.is_symlink() or script.stat().st_size > 16000:
        raise Blocked("unsafe_wave185_node_runner")
    return hashes


def _receipt_ok(parsed: object) -> bool:
    if not isinstance(parsed, dict) or parsed.get("tests_passed") != TEST_COUNT:
        return False
    required_true = (
        "original_grpc_int64_precision_pass",
        "original_kafka_message_conversion_pass",
        "original_grpc_error_sanitization_pass",
    )
    required_false = (
        "external_modules_used", "production_grpc_server_qualified",
        "production_node_grpc_server_qualified", "production_node_worker_qualified", "real_rust_to_production_node_qualified",
        "durable_clickhouse_qualified", "authenticated_tenant_isolation_qualified",
        "release_qualified",
    )
    return all(parsed.get(f) is True for f in required_true) and all(
        parsed.get(f) is False for f in required_false
    )


def qualify(reference: Path, runner_root: Path, node_bin: str = "node") -> dict:
    report: dict[str, object] = {
        "phase": "original-source-offline-node-grpc-precision-redaction",
        "git_attested_original_node_modules": False,
        "original_node_grpc_kafka_primitives_pass": False,
        "production_node_grpc_server_qualified": False,
        "production_node_worker_qualified": False,
        "native_rust_to_production_node_qualified": False,
        "durable_clickhouse_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    try:
        hashes = verified_modules(reference, runner_root)
        report["git_attested_original_node_modules"] = True
        report["original_node_git_blob_sha1"] = hashes
        if node_bin != "node" or not shutil.which(node_bin):
            raise Blocked("unavailable_approved_node_binary")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(runner_root),
               "NODE_OPTIONS": "", "LANG": "C"}
        result = subprocess.run(
            [node_bin, "--no-warnings", "--experimental-strip-types", str(runner_root / RUNNER)],
            cwd=runner_root, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=14,
        )
        if result.returncode or len(result.stdout) > MAX_OUTPUT_BYTES or len(result.stderr) > MAX_OUTPUT_BYTES:
            raise Blocked("native_original_node_grpc_precision_tests_failed")
        try:
            parsed = json.loads(result.stdout)
        except (ValueError, UnicodeError) as exc:
            raise Blocked("invalid_node_primitive_receipt") from exc
        if not _receipt_ok(parsed):
            raise Blocked("node_primitive_qualifier_not_passed")
        report["original_node_grpc_kafka_primitives_pass"] = True
        report["original_node_subtests_passed"] = TEST_COUNT
        report["node_executable_exit_code"] = result.returncode
    except (Blocked, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report["blocker"] = str(exc) if isinstance(exc, Blocked) else type(exc).__name__
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--runner", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    report = qualify(a.reference, a.runner)
    if a.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Flind original Node gRPC primitives:",
              "PASS" if report["original_node_grpc_kafka_primitives_pass"] else "BLOCKED")
    return 0 if report["original_node_grpc_kafka_primitives_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
