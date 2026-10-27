#!/usr/bin/env python3
"""Native Rust Capture→Kafka→actual first-party Node TS adapter→ClickHouse UUID.

Uses synthetic data and a test bridge; does not run the Node gRPC worker,
native Rust ingestion consumer, durable Kafka MV, or authenticated dashboard.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_cached_native_capture_clickhouse_wave182 import (
    qualify as native_to_clickhouse, SUPPORTED_CH_BINARY,
)
from tools.flind.qualify_cached_rust_capture_kafka_wave180 import (
    SYNTHETIC_TOKEN, SYNTHETIC_ID,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/flind/inspect_native_kafka_node_wave183.mjs"
CONVERTER_REL = "nodejs/src/ingestion/api/kafka-message-converter.ts"


class Denied(Exception):
    pass


def verify_source_converter(repo: Path) -> bool:
    file = ROOT / CONVERTER_REL
    if not file.is_file() or file.is_symlink():
        return False
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    try:
        tree = subprocess.run(["git", "-C", str(repo), "ls-tree", "HEAD", "--", CONVERTER_REL],
                              capture_output=True, timeout=12, env=env)
        sha = tree.stdout.decode("ascii").strip().split()
        if tree.returncode or len(sha) != 4 or sha[:2] != ["100644", "blob"]:
            return False
        actual = subprocess.run(["git", "hash-object", str(file)], capture_output=True,
                                timeout=12, env=env)
        return actual.returncode == 0 and actual.stdout.decode("ascii").strip() == sha[2]
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return False


def node_adapter(event: dict, uuid: str, *, node_bin: str = "node") -> dict[str, object]:
    if (type(event) is not dict or event.get("uuid") != uuid
            or event.get("token") != SYNTHETIC_TOKEN
            or event.get("distinct_id") != SYNTHETIC_ID
            or event.get("event") != "$pageview"
            or "team_id" in event):
        raise Denied("native_node_adapter_rejected_untrusted_record")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", uuid):
        raise Denied("native_node_adapter_invalid_uuid")
    if not SCRIPT.is_file() or SCRIPT.is_symlink() or not shutil.which(node_bin):
        raise Denied("native_node_adapter_unavailable")
    payload = json.dumps({
        "topic": "flind_wave180_first_party_native_capture",
        "uuid": uuid,
        "event": event,
    }, separators=(",", ":"))
    if len(payload.encode("utf-8")) > 64 * 1024:
        raise Denied("native_node_adapter_oversized_fixture")
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(ROOT), "LANG": "C", "NODE_OPTIONS": "",
    }
    try:
        node = subprocess.run(
            [node_bin, "--no-warnings", "--experimental-strip-types", str(SCRIPT)],
            input=payload, text=True, capture_output=True, stdin=None,
            cwd=ROOT, env=env, timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Denied("native_node_adapter_process_blocked") from exc
    if node.returncode or len(node.stdout) > 1200:
        raise Denied("native_node_adapter_rejected_fixture")
    try:
        response = json.loads(node.stdout)
    except (ValueError, UnicodeError) as exc:
        raise Denied("native_node_adapter_invalid_receipt") from exc
    if (type(response) is not dict
            or response.get("actual_typescript_deserializer_uuid_verified") is not True
            or response.get("source_record_was_real_native_capture_kafka") is not True
            or response.get("real_node_grpc_worker_qualified") is not False
            or response.get("release_qualified") is not False):
        raise Denied("native_node_adapter_receipt_mismatch")
    return response


def qualify(repo: Path, kafka_home: Path, scratch: Path,
            clickhouse: Path = SUPPORTED_CH_BINARY) -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "real-native-rust-capture-kafka-production-typescript-converter-supported-clickhouse",
        "native_capture_kafka_node_converter_clickhouse_uuid_pass": False,
        "actual_node_ingestion_worker_qualified": False,
        "native_rust_kafka_consumer_qualified": False,
        "durable_clickhouse_ingestion_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "sdk_dashboard_browser_e2e_qualified": False,
        "release_qualified": False,
    }
    try:
        if not verify_source_converter(repo):
            raise Denied("first_party_node_converter_git_blob_mismatch")
        report["first_party_node_converter_source_verified"] = True
        native = native_to_clickhouse(
            repo, kafka_home, scratch, clickhouse,
            on_validated_native_event=node_adapter,
        )
        report["native_capture_kafka_node_converter_clickhouse_uuid_pass"] = all((
            native.get("native_capture_http_kafka_clickhouse_uuid_pass") is True,
            native.get("actual_typescript_deserializer_uuid_verified") is True,
            native.get("owned_kafka_process_stopped") is True,
            native.get("owned_kafka_scratch_removed") is True,
            native.get("owned_capture_stopped") is True,
            native.get("owned_redis7_stopped") is True,
        ))
        report["actual_typescript_deserializer_uuid_verified"] = (
            native.get("actual_typescript_deserializer_uuid_verified") is True
        )
        report["owned_kafka_process_stopped"] = native.get("owned_kafka_process_stopped")
        report["owned_kafka_scratch_removed"] = native.get("owned_kafka_scratch_removed")
        report["native_event_inserted_rows"] = native.get("native_event_inserted_rows", 0)
        report["source_commit"] = native.get("source_commit")
        if not report["native_capture_kafka_node_converter_clickhouse_uuid_pass"]:
            raise Denied(native.get("synthetic_callback_refusal_code")
                         or native.get("blocker") or "node_kafka_to_clickhouse_unavailable")
    except (Denied, OSError, ValueError) as exc:
        report["blocker"] = str(exc) if isinstance(exc, Denied) else type(exc).__name__
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--kafka-home", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--clickhouse", type=Path, default=SUPPORTED_CH_BINARY)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    receipt = qualify(args.repo, args.kafka_home, args.scratch, args.clickhouse)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print("Flind native Capture→Kafka→Node converter→ClickHouse:",
              "PASS" if receipt["native_capture_kafka_node_converter_clickhouse_uuid_pass"] else "BLOCKED")
    return 0 if receipt["native_capture_kafka_node_converter_clickhouse_uuid_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
