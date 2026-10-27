#!/usr/bin/env python3
"""Version-gated real private Kafka -> supported ClickHouse local synthetic relay.

Reads Flind's actual tracked service requirements without importing Django.
No release/tenant-auth/SDK/native product-ingestion claims.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import (
    qualify as real_kafka_relay,
)

REQ_FILE = "posthog/settings/service_requirements.py"
EXPECTED_CH = "clickhouse"
SOURCE_LIMIT_BYTES = 40 * 1024
VERSION = re.compile(r"ClickHouse local version (\d+(?:\.\d+){2,3})\b")
CLAUSE = re.compile(r"(>=|<=|==|<|>)(\d+(?:\.\d+){1,2})\Z")


class Unsupported(Exception):
    pass


def source_clickhouse_spec(repo: Path, ref: str = "HEAD") -> tuple[str, str]:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_OPTIONAL_LOCKS": "0"}
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", ref+"^{commit}"],
                            capture_output=True, env=env, timeout=20)
    sha = commit.stdout.decode("ascii").strip()
    if commit.returncode or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", sha):
        raise Unsupported("unverified_flind_source")
    tree = subprocess.run(["git", "-C", str(repo), "ls-tree", ref, "--", REQ_FILE],
                          capture_output=True, env=env, timeout=20)
    parts = tree.stdout.decode("utf-8").strip().split()
    if tree.returncode or len(parts) != 4 or parts[:2] != ["100644", "blob"]:
        raise Unsupported("unsupported_requirements_source_blob")
    obj = subprocess.run(["git", "-C", str(repo), "show", ref+":"+REQ_FILE],
                         capture_output=True, env=env, timeout=25)
    raw = obj.stdout
    if obj.returncode or len(raw) > SOURCE_LIMIT_BYTES:
        raise Unsupported("requirements_blob_unavailable")
    digest = hashlib.sha1 if len(parts[2]) == 40 else hashlib.sha256
    if digest(f"blob {len(raw)}\0".encode()+raw).hexdigest() != parts[2]:
        raise Unsupported("service_requirements_git_digest_mismatch")
    try:
        found = []
        for node in ast.walk(ast.parse(raw.decode("utf-8"))):
            if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name)
                    or node.func.id != "ServiceVersionRequirement"):
                continue
            values = {key.arg: ast.literal_eval(key.value) for key in node.keywords}
            if values.get("service") == EXPECTED_CH:
                found.append(values.get("supported_version"))
        if len(found) != 1 or not isinstance(found[0], str):
            raise Unsupported("missing_or_ambiguous_clickhouse_requirements")
        return sha, found[0]
    except (SyntaxError, ValueError, TypeError, UnicodeError) as exc:
        raise Unsupported("cannot_safely_parse_flind_requirements") from exc


def version_qualified(value: str, spec: str) -> bool:
    try:
        version = tuple(int(v) for v in value.split("."))
        if len(version) < 3:
            return False
        clauses = [v.strip() for v in spec.split(",")]
        if not clauses or len(clauses) > 5:
            return False
        for clause in clauses:
            match = CLAUSE.fullmatch(clause)
            if not match:
                return False
            op, bound = match.groups()
            boundary = tuple(int(v) for v in bound.split("."))
            x = version[:len(boundary)]
            ok = {
                ">=": x >= boundary, "<=": x <= boundary,
                ">": x > boundary, "<": x < boundary, "==": x == boundary,
            }[op]
            if not ok:
                return False
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def binary_clickhouse_version(binary: Path) -> str:
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise Unsupported("unsupported_binary_path")
    try:
        done = subprocess.run([str(binary), "--version"], stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=9, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unsupported("clickhouse_version_command_unavailable") from exc
    if done.returncode or len(done.stdout) > 1000:
        raise Unsupported("clickhouse_version_command_failed")
    match = VERSION.search(done.stdout.decode("ascii", errors="replace"))
    if not match:
        raise Unsupported("unexpected_clickhouse_version_output")
    return match.group(1)


def qualify(repo: Path, kafka_home: Path, scratch: Path, clickhouse: Path) -> dict:
    result: dict[str, object] = {
        "phase": "source-version-gated-real-kafka-to-clickhouse-local",
        "clickhouse_source_version_supported": False,
        "real_kafka_to_supported_clickhouse_synthetic_relay_qualified": False,
        "production_clickhouse_kafka_ingestion_qualified": False,
        "first_party_rust_to_clickhouse_ingestion_qualified": False,
        "authenticated_tenant_isolation_qualified": False,
        "flind_sdk_dashboard_e2e_qualified": False,
        "release_qualified": False,
    }
    try:
        sha, spec = source_clickhouse_spec(repo)
        installed = binary_clickhouse_version(clickhouse)
        result["source_commit"] = sha
        result["clickhouse_required_range"] = spec
        result["clickhouse_observed_version"] = installed
        if not version_qualified(installed, spec):
            raise Unsupported("clickhouse_binary_outside_first_party_source_range")
        result["clickhouse_source_version_supported"] = True
        inner = real_kafka_relay(repo, kafka_home, scratch, clickhouse=str(clickhouse))
        result["kafka_431_broker_qualified"] = inner.get("kafka_431_broker_qualified") is True
        result["real_kafka_producer_ack_qualified"] = inner.get("real_kafka_producer_ack_qualified") is True
        result["real_kafka_consumer_qualified"] = inner.get("real_kafka_consumer_qualified") is True
        result["owned_kafka_process_stopped"] = inner.get("owned_kafka_process_stopped") is True
        result["owned_kafka_scratch_removed"] = inner.get("owned_kafka_scratch_removed") is True
        result["real_kafka_to_supported_clickhouse_synthetic_relay_qualified"] = all((
            inner.get("local_clickhouse_relay_qualified") is True,
            inner.get("kafka_431_broker_qualified") is True,
            inner.get("real_kafka_producer_ack_qualified") is True,
            inner.get("real_kafka_consumer_qualified") is True,
            inner.get("owned_kafka_process_stopped") is True,
            inner.get("owned_kafka_scratch_removed") is True,
        ))
        result["synthetic_kafka_records"] = inner.get("synthetic_kafka_event_count", 0)
        result["clickhouse_inserted_rows"] = inner.get("synthetic_rows_inserted", 0)
        if not result["real_kafka_to_supported_clickhouse_synthetic_relay_qualified"]:
            raise Unsupported(inner.get("blocker", "supported_synthetic_relay_unavailable"))
    except (Unsupported, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["blocker"] = str(exc) if isinstance(exc, Unsupported) else type(exc).__name__
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--kafka-home", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--clickhouse", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = qualify(args.repo, args.kafka_home, args.scratch, args.clickhouse)
    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print("Flind Kafka → supported ClickHouse:",
              "PASS" if output["real_kafka_to_supported_clickhouse_synthetic_relay_qualified"] else "BLOCKED")
    return 0 if output["real_kafka_to_supported_clickhouse_synthetic_relay_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
