#!/usr/bin/env python3
"""Read-only, no-network coverage preflight for first-party Flind Django Python source.

A sparse/partial checkout can have a complete Git tree but lack both the working-tree
file and the local blob needed for import. Never trigger Git lazy fetching and never
confuse an installed Django wheel with an importable application registry.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOTS = ("posthog", "products", "ee", "common", "flind")
REF_PATTERN = re.compile(r"^[A-Za-z0-9_./-]{1,128}$")
MAX_TRACKED = 50_000
MAX_OUTPUT = 32 * 1024 * 1024


def git_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }


def git_read(root: Path, args: list[str], *, input_data: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_data,
        capture_output=True,
        timeout=35,
        check=False,
        env=git_env(),
    )
    if completed.returncode != 0 or len(completed.stdout) > MAX_OUTPUT:
        raise RuntimeError("Offline Git source inventory unavailable")
    return completed.stdout


def tracked_python(root: Path, ref: str) -> list[tuple[str, str]]:
    if not REF_PATTERN.fullmatch(ref) or ref.startswith("-") or ".." in ref.split("/"):
        raise ValueError("Invalid source ref")
    output = git_read(
        root,
        ["ls-tree", "-r", "-z", "--format=%(objectname)%x09%(path)", ref, "--", *ROOTS],
    )
    result: list[tuple[str, str]] = []
    for item in output.split(b"\0"):
        if not item:
            continue
        try:
            oid, path = item.decode("utf-8").split("\t", 1)
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("Invalid tracked source path encoding") from exc
        if not path.endswith(".py"):
            continue
        if (not re.fullmatch("[0-9a-f]{40,64}", oid)
                or Path(path).is_absolute()
                or ".." in Path(path).parts
                or path.split("/", 1)[0] not in ROOTS):
            raise RuntimeError("Invalid tracked source entry")
        result.append((oid, path))
        if len(result) > MAX_TRACKED:
            raise RuntimeError("Tracked source count exceeds safety budget")
    return result


def available_local_blobs(root: Path, oids: list[str]) -> set[str]:
    """One no-lazy-fetch batch check; never download Git promisor objects."""
    if not oids:
        return set()
    unique = list(dict.fromkeys(oids))
    output = git_read(
        root,
        ["cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input_data=("\n".join(unique) + "\n").encode("ascii"),
    )
    lines = output.decode("ascii").splitlines()
    if len(lines) != len(unique):
        raise RuntimeError("Git blob inventory returned an inconsistent count")
    available: set[str] = set()
    for oid, line in zip(unique, lines, strict=True):
        if line == f"{oid} blob":
            available.add(oid)
        elif line != f"{oid} missing":
            raise RuntimeError("Git blob inventory returned an invalid record")
    return available


def qualify(root: Path, ref: str = "HEAD") -> dict[str, object]:
    result: dict[str, object] = {
        "phase": "offline-django-source-coverage",
        "source_ref": ref,
        "django_registry_qualified": False,
        "migrations_qualified": False,
        "end_to_end_qualified": False,
        "release_qualified": False,
        "source_coverage_qualified": False,
    }
    try:
        if not (root / "pyproject.toml").is_file():
            raise RuntimeError("Flind project root missing")
        tracked = tracked_python(root, ref)
        if not tracked:
            raise RuntimeError("No tracked first-party Python sources")
        available = available_local_blobs(root, [oid for oid, _ in tracked])
        by_root: dict[str, Counter[str]] = {k: Counter() for k in ROOTS}
        missing_examples: list[str] = []
        in_worktree = 0
        blob_backed_only = 0
        unavailable = 0
        for oid, name in tracked:
            root_name = name.split("/", 1)[0]
            by_root[root_name]["tracked"] += 1
            if (root / name).is_file():
                in_worktree += 1
                by_root[root_name]["worktree"] += 1
            elif oid in available:
                blob_backed_only += 1
                by_root[root_name]["git_blob_only"] += 1
            else:
                unavailable += 1
                by_root[root_name]["unavailable"] += 1
                if len(missing_examples) < 8:
                    missing_examples.append(name)
        result.update({
            "tracked_python": len(tracked),
            "present_in_worktree": in_worktree,
            "available_only_as_local_git_blob": blob_backed_only,
            "unavailable_without_fetch": unavailable,
            "coverage_by_root": {k: dict(by_root[k]) for k in ROOTS},
            "missing_examples": missing_examples,
            "source_coverage_qualified": unavailable == 0,
        })
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        # Never echo filesystem, network or Git exceptions.
        result["blocker"] = type(exc).__name__
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = qualify(Path(args.root).resolve(), args.ref)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Flind offline source coverage:",
              "AVAILABLE" if report["source_coverage_qualified"] else "BLOCKED")
        print("Django registry/migrations/E2E/release: NOT QUALIFIED")
    return 0 if report["source_coverage_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())