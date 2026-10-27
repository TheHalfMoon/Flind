#!/usr/bin/env python3
"""Qualify the original first-party Node WorkerIngestServer over real HTTP/2/gRPC.

Uses 8 SHA-verified Git source modules, actual pinned Connect/Protobuf/Prom
packages and original first-party Connect HTTP/2 patch in a marked scratch.
Only the logger and ingestion driver are isolated test doubles. No production
pipeline, native Rust client, tenant auth or durable ClickHouse is qualified.
Never installs packages or contacts external services.
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
import time

SRC = (
    "nodejs/src/ingestion/api/grpc-server.ts",
    "nodejs/src/ingestion/api/grpc-message-converter.ts",
    "nodejs/src/ingestion/api/grpc-error-sanitizer.ts",
    "nodejs/src/ingestion/api/batch-metrics.ts",
    "nodejs/src/ingestion/api/feed-order-sentinel.ts",
    "nodejs/src/ingestion/api/types.ts",
    "nodejs/src/ingestion/framework/batch-budget.ts",
    "nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts",
)
VERSIONS = {
    "@bufbuild/protobuf": "2.11.0",
    "@connectrpc/connect": "2.1.1",
    "@connectrpc/connect-node": "2.1.1",
    "prom-client": "14.2.0",
    "esbuild": "0.25.12",
}
MARKER = ".flind-wave186-owner"
MARKER_VALUE = "FLIND_WAVE186_OWNED_GRPC_CORE_V1\n"
LOGGER_SHIM = "export const logger = {info:()=>{},warn:()=>{},error:()=>{},debug:()=>{}}\n"
BUILDER = "tools/flind/build_actual_node_grpc_http2_wire_wave186.mjs"
TESTER = "tools/flind/verify_actual_node_grpc_http2_wire_wave186.mjs"
COUNT = 20


class Denied(ValueError):
    pass


def original_blob(repo: Path, relative: str) -> tuple[str, bytes]:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    try:
        r = subprocess.run(["git", "-C", str(repo), "ls-tree", "HEAD", "--", relative],
                           capture_output=True, timeout=15, env=env, check=False)
        parts = r.stdout.decode("ascii").strip().split()
        if r.returncode or len(parts) != 4 or parts[:2] != ["100644", "blob"]:
            raise Denied("unavailable_original_git_source")
        oid = parts[2]
        if not re.fullmatch(r"[0-9a-f]{40}", oid):
            raise Denied("invalid_original_source_oid")
        v = subprocess.run(["git", "-C", str(repo), "show", "HEAD:" + relative],
                           capture_output=True, timeout=18, env=env, check=False)
        if v.returncode or len(v.stdout) > 50000:
            raise Denied("original_source_blob_missing_or_oversized")
        digest = hashlib.sha1(f"blob {len(v.stdout)}\0".encode() + v.stdout).hexdigest()
        if digest != oid:
            raise Denied("original_source_git_blob_hash_mismatch")
        return oid, v.stdout
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise Denied("original_source_git_unavailable") from exc


def admitted(repo: Path, scratch: Path, script_root: Path) -> None:
    base = Path("/private/tmp").resolve()
    if (repo.is_symlink() or not repo.is_dir()
            or scratch.is_symlink() or not scratch.is_dir()
            or scratch.resolve().parent != base
            or repo.resolve() == scratch.resolve()
            or script_root.is_symlink() or not script_root.is_dir()):
        raise Denied("original_source_or_scratch_scope_refused")
    marker = scratch / MARKER
    if marker.is_symlink() or not marker.is_file() or marker.read_text() != MARKER_VALUE:
        raise Denied("unowned_node_grpc_scratch")
    if shutil.disk_usage(scratch).free < 3 * (1024**3):
        raise Denied("insufficient_disk_reserve")


def checked_dependencies(scratch: Path) -> None:
    for name, version in VERSIONS.items():
        package = scratch / "node_modules" / name / "package.json"
        if not package.is_file():
            raise Denied("missing_pinned_real_grpc_dependency")
        try:
            got = json.loads(package.read_text()).get("version")
        except (ValueError, UnicodeError) as exc:
            raise Denied("bad_grpc_package_manifest") from exc
        if got != version:
            raise Denied("unapproved_real_grpc_dependency_version")
    # Flind's lockfile patches Connect's deferred HTTP2 GOAWAY error handling.
    for layout in ("esm", "cjs"):
        target = (scratch / "node_modules/@connectrpc/connect-node/dist"
                  / layout / "http2-session-manager.js")
        if not target.is_file() or "conn.once(\"error\", () => {" not in target.read_text():
            raise Denied("missing_first_party_connect_http2_patch")


def original_sources(repo: Path, scratch: Path) -> dict[str, str]:
    attested: dict[str, str] = {}
    root = scratch / "firstparty"
    for relative in SRC:
        oid, blob = original_blob(repo, relative)
        path = root / relative
        if path.exists() and (path.is_symlink() or not path.is_file()):
            raise Denied("unexpected_preexisting_source_path")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        attested[relative] = oid
    shim = root / "nodejs/src/common/utils/logger.ts"
    if shim.exists() and shim.is_symlink():
        raise Denied("symlinked_test_logger_shim")
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(LOGGER_SHIM)
    return attested


def copy_fixture(script_root: Path, scratch: Path) -> None:
    for filename, destination in ((BUILDER, "build-wire.mjs"),
                                  (TESTER, "test-wire.mjs")):
        source = script_root / filename
        target = scratch / destination
        if source.is_symlink() or not source.is_file() or source.stat().st_size > 14000:
            raise Denied("unavailable_first_party_wire_fixture")
        if target.is_symlink():
            raise Denied("symlinked_scratch_wire_fixture")
        target.write_bytes(source.read_bytes())


def receipt_ok(receipt: object) -> bool:
    if not isinstance(receipt, dict):
        return False
    yes = ("actual_first_party_grpc_server_started", "real_grpc_http2_handshake_and_ack",
           "unsafe_sequence_rejected")
    no = ("first_party_node_worker_pipeline_qualified", "first_party_rust_to_node_qualified",
          "durable_clickhouse_qualified", "authenticated_tenant_isolation_qualified",
          "release_qualified")
    return (receipt.get("assertions_passed") == COUNT
            and all(receipt.get(x) is True for x in yes)
            and all(receipt.get(x) is False for x in no))


def run(repo: Path, scratch: Path, script_root: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "phase": "source-attested-original-node-http2-grpc-wire",
        "real_first_party_http2_grpc_worker_server_qualified": False,
        "production_ingestion_driver_qualified": False,
        "real_rust_to_production_node_qualified": False,
        "durable_clickhouse_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    start = time.monotonic()
    try:
        admitted(repo, scratch, script_root)
        checked_dependencies(scratch)
        result["first_party_source_git_blobs"] = original_sources(repo, scratch)
        copy_fixture(script_root, scratch)
        if not shutil.which("node"):
            raise Denied("node_binary_missing")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "HOME": str(scratch), "LANG": "C", "NODE_OPTIONS": ""}
        build = subprocess.run(["node", "build-wire.mjs"], cwd=scratch, env=env,
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
        if build.returncode or b"FLIND_FIRST_PARTY_ESBUILD_PASS" not in build.stdout:
            raise Denied("original_grpc_http2_bundle_failed")
        app = subprocess.run(["node", "dist/test-wire.mjs"], cwd=scratch, env=env,
                             stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
        if app.returncode or len(app.stdout) > 3000 or len(app.stderr) > 3000:
            raise Denied("real_original_http2_grpc_wire_failed")
        try:
            data = json.loads(app.stdout)
        except (ValueError, UnicodeError) as exc:
            raise Denied("invalid_real_grpc_wire_receipt") from exc
        if not receipt_ok(data):
            raise Denied("original_grpc_http2_wire_not_qualified")
        result["real_first_party_http2_grpc_worker_server_qualified"] = True
        result["synthetic_wire_assertions_passed"] = COUNT
        result["actual_http2_connect_grpc_transport"] = True
        result["actual_first_party_connect_patch_applied"] = True
        result["node_exit_code"] = app.returncode
    except (Denied, OSError, subprocess.TimeoutExpired) as exc:
        result["blocker"] = str(exc) if isinstance(exc, Denied) else type(exc).__name__
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - start, 1)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--scripts-root", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    result = run(args.reference, args.scratch, args.scripts_root)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else
          "Flind original WorkerIngestServer real HTTP/2/gRPC: " +
          ("PASS" if result["real_first_party_http2_grpc_worker_server_qualified"] else "BLOCKED"))
    return 0 if result["real_first_party_http2_grpc_worker_server_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
