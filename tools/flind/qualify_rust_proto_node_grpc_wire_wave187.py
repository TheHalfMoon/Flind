#!/usr/bin/env python3
"""Original typed Rust Protobuf client -> actual first-party Node gRPC wire.

Fully synthetic, local integration. Uses a test-only ingestion driver and
logger; this does not run the production Rust Kafka consumer or Node pipeline.
No installs, no cloud APIs, no actual customer events.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind import qualify_actual_node_grpc_http2_wire_wave186 as w186

NODE_SERVER = "tools/flind/verify_rust_proto_node_server_wave187.mjs"
NODE_BUILDER = "tools/flind/build_rust_proto_node_server_wave187.mjs"
RUST_CLIENT = "tools/flind/wave187-rust-client/src/main.rs"
RUST_MANIFEST = "tools/flind/wave187-rust-client/Cargo.toml"
RUST_MARKER = ".flind-wave187-rust-owner"
RUST_MARKER_VALUE = "FLIND_WAVE187_RUST_CLIENT_V1\n"
RUST_PROTO_SOURCE = (
    "rust/ingestion-worker-proto/src/lib.rs",
    "rust/ingestion-worker-proto/build.rs",
    "proto/ingestion/worker/v1/worker.proto",
)
SUCCESS = ("original_rust_proto_client_wire_pass", "real_node_http2_ack_verified", "bad_rust_seq_refused")
FALSE = ("production_rust_ingestion_consumer_qualified", "production_node_driver_qualified", "durable_clickhouse_qualified", "release_qualified")


class Rejected(ValueError):
    pass


def original_rust_sources(reference: Path, checkout: Path, runner: Path, rust: Path) -> dict[str, str]:
    if (rust.is_symlink() or rust.resolve().parent != Path("/private/tmp").resolve()
            or not rust.is_dir() or checkout.is_symlink() or not checkout.is_dir()
            or not (rust / RUST_MARKER).is_file()
            or (rust / RUST_MARKER).read_text() != RUST_MARKER_VALUE):
        raise Rejected("unowned_or_missing_original_rust_source_checkout")
    attested = {}
    for rel in RUST_PROTO_SOURCE:
        oid, content = w186.original_blob(reference, rel)
        file = checkout / rel
        if not file.is_file() or file.is_symlink() or file.read_bytes() != content:
            raise Rejected("original_rust_proto_source_drift")
        attested[rel] = oid
    for rel, path in ((RUST_CLIENT, rust / "src/main.rs"), (RUST_MANIFEST, rust / "Cargo.toml")):
        expected = runner / rel
        if not expected.is_file() or expected.is_symlink() or path.is_symlink() or not path.is_file():
            raise Rejected("unavailable_tracked_rust_wire_fixture")
        literal = expected.read_text()
        if rel == RUST_MANIFEST:
            literal = literal.replace(
                "../../../rust/ingestion-worker-proto",
                str(checkout / "rust/ingestion-worker-proto"),
            )
        if path.read_text() != literal:
            raise Rejected("modified_original_rust_client_fixture")
    return attested


def fixture_scripts(runner: Path, scratch: Path) -> None:
    for rel, name in ((NODE_BUILDER, "build-rust-wire.mjs"), (NODE_SERVER, "server-rust-wire.mjs")):
        source = runner / rel
        if not source.is_file() or source.is_symlink() or source.stat().st_size > 12000:
            raise Rejected("unavailable_first_party_node_wire_fixture")
        target = scratch / name
        if target.is_symlink():
            raise Rejected("unsafe_node_scratch_script")
        target.write_bytes(source.read_bytes())


def receipt_ok(native: object, stopped: object) -> bool:
    return (
        isinstance(native, dict)
        and all(native.get(key) is True for key in SUCCESS)
        and all(native.get(key) is False for key in FALSE)
        and isinstance(stopped, dict)
        and stopped.get("flind_wave187") == "server_stopped"
        and type(stopped.get("accepted_synthetic_batches")) is int
        and stopped["accepted_synthetic_batches"] == 1
    )


def real_wire(node_scratch: Path, rust_scratch: Path) -> dict:
    result: dict[str, Any] = {}
    node = None
    try:
        node = subprocess.Popen(
            ["node", "dist/server-rust-wire.mjs"], cwd=node_scratch,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, start_new_session=True,
            env={**os.environ, "NODE_OPTIONS": ""},
        )
        assert node.stdout is not None
        ready, _, _ = select.select([node.stdout], [], [], 10)
        if not ready:
            raise Rejected("real_first_party_node_grpc_start_timeout")
        line = node.stdout.readline().strip()
        if len(line) > 500:
            raise Rejected("oversized_node_grpc_listener_receipt")
        listener = json.loads(line)
        port = listener.get("port")
        if (listener.get("flind_wave187") != "listening"
                or type(port) is not int or port < 1024 or port > 65535):
            raise Rejected("invalid_local_test_grpc_listener")
        native_path = rust_scratch / "target/debug/flind-wave187-rust-grpc-client"
        if native_path.is_symlink() or not native_path.is_file():
            raise Rejected("missing_compiled_original_rust_proto_test_client")
        native = subprocess.run(
            [str(native_path)], cwd=rust_scratch,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=35,
            env={**os.environ, "FLIND_WAVE187_NODE_PORT": str(port)},
        )
        if native.returncode or len(native.stdout) > 3000 or len(native.stderr) > 3000:
            raise Rejected("original_rust_to_node_grpc_wire_failed")
        result["native"] = json.loads(native.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["blocker"] = str(exc) if isinstance(exc, Rejected) else type(exc).__name__
    finally:
        if node:
            if node.poll() is None:
                os.killpg(node.pid, signal.SIGTERM)
            try:
                node.wait(timeout=7)
            except subprocess.TimeoutExpired:
                os.killpg(node.pid, signal.SIGKILL)
                node.wait(timeout=4)
            result["node_exit_code"] = node.returncode
            if node.stdout:
                output = node.stdout.read(1200)
                try:
                    result["stop_receipt"] = json.loads(output.strip())
                except (ValueError, UnicodeError):
                    result["stop_receipt"] = {}
                node.stdout.close()
            if node.stderr:
                node.stderr.close()
    result["qualified"] = bool(
        receipt_ok(result.get("native"), result.get("stop_receipt"))
        and result.get("node_exit_code") == 0
    )
    return result


def qualify(reference: Path, checkout: Path, runner: Path, node: Path, rust: Path) -> dict:
    report: dict[str, Any] = {
        "phase": "original_rust_proto_to_actual_node_http2_grpc_wire",
        "original_rust_proto_to_real_node_grpc_qualified": False,
        "production_rust_kafka_ingestion_consumer_qualified": False,
        "production_node_ingestion_driver_qualified": False,
        "durable_clickhouse_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    start = time.monotonic()
    try:
        w186.admitted(reference, node, runner)
        w186.checked_dependencies(node)
        report["original_rust_proto_source_sha1"] = original_rust_sources(reference, checkout, runner, rust)
        report["original_node_source_sha1"] = w186.original_sources(reference, node)
        fixture_scripts(runner, node)
        if not shutil.which("node"):
            raise Rejected("node26_unavailable")
        builder = subprocess.run(["node", "build-rust-wire.mjs"], cwd=node,
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=18)
        if builder.returncode or b"FLIND_ORIGINAL_NODE_GRPC_SERVER_COMPILED" not in builder.stdout:
            raise Rejected("original_node_grpc_test_server_build_failed")
        wire = real_wire(node, rust)
        report["original_rust_proto_to_real_node_grpc_qualified"] = wire["qualified"]
        report["rust_node_ack_count"] = (wire.get("stop_receipt") or {}).get("accepted_synthetic_batches", 0)
        report["node_server_stopped"] = wire.get("node_exit_code") == 0
        if not wire["qualified"]:
            raise Rejected(wire.get("blocker") or "original_rust_node_wire_not_qualified")
    except (Rejected, w186.Denied, OSError, subprocess.TimeoutExpired) as exc:
        report["blocker"] = str(exc) if isinstance(exc, (Rejected, w186.Denied)) else type(exc).__name__
    report["elapsed_seconds"] = round(time.monotonic()-start, 1)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--runner", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--node-scratch", type=Path, required=True)
    p.add_argument("--rust-scratch", type=Path, required=True)
    p.add_argument("--json", action="store_true")
    a=p.parse_args()
    r=qualify(a.reference,a.checkout,a.runner,a.node_scratch,a.rust_scratch)
    print(json.dumps(r,indent=2,sort_keys=True) if a.json else
          ("Flind first-party Rust→real Node gRPC: "+"PASS" if r["original_rust_proto_to_real_node_grpc_qualified"] else "BLOCKED"))
    return 0 if r["original_rust_proto_to_real_node_grpc_qualified"] else 2


if __name__=="__main__":
    raise SystemExit(main())
