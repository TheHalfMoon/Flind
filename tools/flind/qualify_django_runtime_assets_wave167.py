#!/usr/bin/env python3
"""Offline Flind runtime-asset availability preflight (not Django or release qualification).

Distinguishes a tracked runtime candidate from a file in the sparse worktree,
a local-only Git blob, and a blob that cannot be read without fetching. Never
hydrates assets, connects to services, or assumes all candidates are required.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

from tools.flind.qualify_django_source_coverage_wave165 import (
    ROOTS, git_env,
)


def git_read(root: Path, args: list[str], *, input_data: bytes | None = None) -> bytes:
    # Packed repositories can need more than the Python-source inventory's 35s.
    result = subprocess.run(
        ["git", "-C", str(root), *args], input=input_data,
        capture_output=True, check=False, timeout=95, env=git_env(),
    )
    if result.returncode or len(result.stdout) > 32 * 1024 * 1024:
        raise RuntimeError("Offline Git resource read unavailable")
    return result.stdout


def available_local_blobs(root: Path, oids: list[str]) -> set[str]:
    unique = list(dict.fromkeys(oids))
    if not unique:
        return set()
    raw = git_read(
        root, ["cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input_data=("\n".join(unique) + "\n").encode("ascii"),
    )
    lines = raw.decode("ascii").splitlines()
    if len(lines) != len(unique):
        raise RuntimeError("Offline resource inventory count mismatch")
    available = set()
    for oid, line in zip(unique, lines, strict=True):
        if line == f"{oid} blob":
            available.add(oid)
        elif line != f"{oid} missing":
            raise RuntimeError("Invalid offline resource record")
    return available


# Runtime candidates in first-party paths. This is NOT a dependency graph.
RUNTIME_SUFFIXES = frozenset({
    ".hog", ".json", ".yaml", ".yml", ".toml", ".sql", ".graphql", ".proto", ".csv"
})
# Exact resources proven necessary by Wave 166 bounded startup traces.
TRACED_REQUIRED = (
    "products/growth/backend/enrichment/scoring_formula.hog",
    "products/alerts/backend/logic/destination_stock_inputs.json",
)
MAX_ASSETS = 45000
VALID_OID = re.compile(r"[0-9a-f]{40,64}\Z")
VALID_REF = re.compile(r"[A-Za-z0-9_./-]{1,128}\Z")


def tracked_assets(root: Path, ref: str, *, scope: str = "traced") -> list[tuple[str, str]]:
    if scope not in ("traced", "all"):
        raise ValueError("Invalid asset scope")
    if not VALID_REF.fullmatch(ref) or ref.startswith("-") or ".." in ref.split("/"):
        raise ValueError("Unsafe source ref")
    output = git_read(
        root,
        ["ls-tree", "-r", "-z",
         "--format=%(objectmode)%x09%(objecttype)%x09%(objectname)%x09%(path)",
         ref, "--", *(TRACED_REQUIRED if scope == "traced" else ROOTS)],
    )
    rows: list[tuple[str, str]] = []
    for record in output.split(b"\x00"):
        if not record:
            continue
        try:
            mode, kind, oid, name = record.decode("utf-8").split("\t", 3)
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("Invalid offline tracked asset record") from exc
        path = Path(name)
        if path.suffix.lower() not in RUNTIME_SUFFIXES:
            continue
        if (mode not in ("100644", "100755")
                or kind != "blob" or not VALID_OID.fullmatch(oid)
                or path.is_absolute() or ".." in path.parts
                or path.parts[0] not in ROOTS):
            raise RuntimeError("Invalid tracked first-party asset")
        rows.append((oid, name))
        if len(rows) > MAX_ASSETS:
            raise RuntimeError("Offline asset inventory exceeded bounded size")
    return rows


def qualify_assets(root: Path, ref: str = "HEAD", *, scope: str = "traced") -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "offline-django-runtime-asset-candidates",
        "source_ref": ref,
        "scope": scope,
        "asset_coverage_qualified": False,
        "django_registry_qualified": False,
        "migrations_qualified": False,
        "end_to_end_qualified": False,
        "release_qualified": False,
    }
    try:
        if not (root / "pyproject.toml").is_file():
            raise RuntimeError("Flind project root missing")
        entries = tracked_assets(root, ref, scope=scope)
        if not entries:
            raise RuntimeError("No tracked runtime candidates")
        # Never query blob objects already materialized in the worktree.
        absent_oids = [oid for oid, name in entries if not (root / name).is_file()]
        available_oids = available_local_blobs(root, absent_oids)
        counts: Counter[str] = Counter()
        by_suffix: dict[str, Counter[str]] = {
            suffix: Counter() for suffix in sorted(RUNTIME_SUFFIXES)
        }
        by_path = {}
        for oid, name in entries:
            suffix = Path(name).suffix.lower()
            exists = (root / name).is_file()
            status = (
                "worktree" if exists else
                "git_blob_only" if oid in available_oids else
                "unavailable"
            )
            counts[status] += 1
            by_suffix[suffix][status] += 1
            by_path[name] = status
        traced = {
            name: by_path.get(name, "not_tracked_at_ref")
            for name in TRACED_REQUIRED
        }
        unavailable_examples = sorted(
            name for name, status in by_path.items() if status == "unavailable"
        )[:12]
        report.update({
            "candidate_suffixes": sorted(RUNTIME_SUFFIXES),
            "tracked_candidates": len(entries),
            "present_in_worktree": counts["worktree"],
            "available_only_as_local_git_blob": counts["git_blob_only"],
            "unavailable_without_fetch": counts["unavailable"],
            "by_suffix": {suffix: {
                "tracked": sum(values.values()),
                "worktree": values["worktree"],
                "git_blob_only": values["git_blob_only"],
                "unavailable": values["unavailable"],
            } for suffix, values in by_suffix.items()},
            "traced_required_resources": traced,
            "unavailable_examples": unavailable_examples,
            # This is only candidate availability, never a deployment approval.
            "asset_coverage_qualified": (
                counts["unavailable"] == 0 and
                all(status == "worktree" for status in traced.values())
            ),
        })
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        report["blocker"] = type(exc).__name__
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--scope", choices=("traced", "all"), default="traced")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_assets(Path(args.root).resolve(), args.ref, scope=args.scope)
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print("Flind runtime-asset candidate coverage:",
              "PRESENT" if result["asset_coverage_qualified"] else "BLOCKED")
        print("Django registry/migrations/E2E/release: NOT QUALIFIED")
    return 0 if result["asset_coverage_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())