#!/usr/bin/env python3
"""Read-only audit of actual installed runtime distributions versus Flind uv.lock.

Must be executed using the target runtime interpreter. Does NOT run the
Django application, execute migrations, install packages, or contact networks.
"""
from __future__ import annotations

import argparse
import ast
from importlib import metadata
import json
import platform
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*")
VALID_MARKER_NAMES = {"sys_platform", "platform_machine"}


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def marker_matches(expr: str, *, sys_platform: str, machine: str) -> bool:
    """Small fail-closed subset of PEP 508 marker syntax used in Flind."""
    values = {"sys_platform": sys_platform, "platform_machine": machine}

    def walk(node: ast.AST) -> str | bool:
        if isinstance(node, ast.Name) and node.id in VALID_MARKER_NAMES:
            return values[node.id]
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            lhs, rhs = walk(node.left), walk(node.comparators[0])
            if not isinstance(lhs, str) or not isinstance(rhs, str):
                raise ValueError("Unsupported marker operand")
            if isinstance(node.ops[0], ast.Eq):
                return lhs == rhs
            if isinstance(node.ops[0], ast.NotEq):
                return lhs != rhs
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            checks = [walk(item) for item in node.values]
            if not all(isinstance(check, bool) for check in checks):
                raise ValueError("Unsupported marker combination")
            return all(checks) if isinstance(node.op, ast.And) else any(checks)
        raise ValueError("Unsupported runtime environment marker")

    result = walk(ast.parse(expr, mode="eval").body)
    if not isinstance(result, bool):
        raise ValueError("Incomplete marker")
    return result


def installed_packages() -> dict[str, str]:
    result: dict[str, str] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            result[canonical(name)] = dist.version
    return result


def audit_runtime_lock(
    root: Path = ROOT,
    installed: dict[str, str] | None = None,
    sys_platform: str = sys.platform,
    machine: str = platform.machine(),
) -> dict:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    locked = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    installed = installed if installed is not None else installed_packages()
    manifest = project["project"]["dependencies"]
    lock_versions = {
        canonical(pkg["name"]): pkg.get("version")
        for pkg in locked["package"]
    }
    missing: list[str] = []
    mismatch: list[dict] = []
    unlocked: list[str] = []
    marker_unverified: list[str] = []
    excluded: list[str] = []
    installed_ok = 0
    expected = 0
    for text in manifest:
        match = NAME_RE.match(text)
        if not match:
            raise ValueError("Invalid direct requirement")
        name = canonical(match.group())
        if ";" in text:
            marker = text.split(";", 1)[1].strip()
            try:
                applies = marker_matches(marker, sys_platform=sys_platform, machine=machine)
            except (SyntaxError, ValueError):
                marker_unverified.append(name)
                continue
            if not applies:
                excluded.append(name)
                continue
        expected += 1
        lock_version = lock_versions.get(name)
        version = installed.get(name)
        if not lock_version:
            unlocked.append(name)
        elif version is None:
            missing.append(name)
        elif version != lock_version:
            mismatch.append({"name": name, "locked": lock_version, "installed": version})
        else:
            installed_ok += 1
    ready = not (missing or mismatch or unlocked or marker_unverified) and expected == installed_ok
    return {
        "phase": "django-dependency-lock",
        "runtime_direct_dependencies": len(manifest),
        "applicable_direct_dependencies": expected,
        "installed_locked_direct_dependencies": installed_ok,
        "missing_count": len(missing),
        "version_mismatch_count": len(mismatch),
        "unlocked_count": len(unlocked),
        "unverified_marker_count": len(marker_unverified),
        "platform_excluded": excluded,
        "missing": missing,
        "version_mismatches": mismatch,
        "unlocked": unlocked,
        "unverified_markers": marker_unverified,
        "direct_lock_qualified": ready,
        "django_boot_qualified": False,
        "release_qualified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = audit_runtime_lock()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for field in (
            "runtime_direct_dependencies", "applicable_direct_dependencies",
            "installed_locked_direct_dependencies", "missing_count",
            "version_mismatch_count", "unlocked_count",
            "unverified_marker_count",
        ):
            print(field + ": " + str(result[field]))
        print("Flind Django lock: " +
              ("QUALIFIED" if result["direct_lock_qualified"] else "BLOCKED"))
        print("Flind Django boot and release E2E: NOT QUALIFIED")
    return 0 if result["direct_lock_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
