#!/usr/bin/env python3
"""Inspect operator-selected local Redis/ClickHouse executable versions.

This checks declared compatibility, not a running service or Flind release.
No background daemons, shared databases, cloud or installer are touched.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

if __package__:
    from .qualify_service_versions import source_requirements, version_matches_spec
else:
    from qualify_service_versions import source_requirements, version_matches_spec


PATTERNS = {
    "redis": re.compile(r"\bv=(\d+\.\d+\.\d+)\b"),
    "clickhouse": re.compile(r"\b(?:version )?(\d+\.\d+\.\d+(?:\.\d+)?)\b"),
}
ALLOWED_SERVICES = ("redis", "clickhouse")


def inspect_binary(service: str, binary: str, required_version: str) -> dict:
    result = {
        "service": service,
        "binary_exists_and_executable": False,
        "observed_version": None,
        "required_version": required_version,
        "supported_version": False,
    }
    if service not in ALLOWED_SERVICES or not isinstance(binary, str) or len(binary) > 4096:
        return result
    try:
        target = Path(binary)
        if not target.is_absolute() or not target.is_file() or not os.access(target, os.X_OK):
            return result
    except (OSError, ValueError):
        return result
    result["binary_exists_and_executable"] = True
    try:
        # Don't invoke a shell or interpolate shell commands; output is capped
        # and never shown. Some first-run signed macOS binaries take ~15 sec.
        child = subprocess.run(
            [str(target), "--version"],
            capture_output=True, text=True, timeout=55, check=False,
        )
        if child.returncode or len(child.stdout) + len(child.stderr) > 4096:
            return result
        match = PATTERNS[service].search(child.stdout + "\n" + child.stderr)
        if match is None:
            return result
        version = match.group(1)
        result["observed_version"] = version
        result["supported_version"] = version_matches_spec(version, required_version)
    except (OSError, subprocess.TimeoutExpired, UnicodeError, ValueError):
        pass
    return result


def qualify_binary_versions(redis_binary: str, clickhouse_binary: str) -> dict:
    receipt = {
        "service_binary_versions_qualified": False,
        "services": [],
        "runtime_service_qualified": False,
        "full_application_qualified": False,
        "sdk_event_ingestion_qualified": False,
        "release_qualified": False,
    }
    try:
        requirements = source_requirements()
    except (OSError, ValueError, SyntaxError, TypeError):
        return {**receipt, "blocker": "Source service requirements unavailable"}
    checks = [
        inspect_binary("redis", redis_binary, requirements["redis"]),
        inspect_binary("clickhouse", clickhouse_binary, requirements["clickhouse"]),
    ]
    passed = bool(len(checks) == 2 and all(item["supported_version"] for item in checks))
    return {
        **receipt,
        "service_binary_versions_qualified": passed,
        "services": checks,
        **({"blocker": "Selected local Redis or ClickHouse version is incompatible/unavailable"}
           if not passed else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--redis-bin", required=True, help="Absolute local redis-server path")
    parser.add_argument("--clickhouse-bin", required=True, help="Absolute local clickhouse path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    receipt = qualify_binary_versions(args.redis_bin, args.clickhouse_bin)
    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print("Flind local binary version compatibility:",
              "PASS" if receipt["service_binary_versions_qualified"] else "BLOCKED")
        print("Actual backend services, SDK and release: NOT QUALIFIED")
    return 0 if receipt["service_binary_versions_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
