#!/usr/bin/env python3
"""Audit and optionally materialize verified Django migration files in marked scratch clone.

Never accesses a DB, never lazy-fetches Git objects, never qualifies the release.
The destination must be a disposable Git checkout with an explicit safety marker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOTS = ("posthog", "products", "ee", "common", "flind")
MARKER = ".flind-migration-scratch-v1"
MARKER_TEXT = "FLIND_MIGRATION_SCRATCH_V1\n"
MAX_FILES = 8000
MAX_BLOB_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
SAFE_REF = re.compile(r"[A-Za-z0-9_./-]{1,128}\Z")
SAFE_FILE = re.compile(r"[A-Za-z0-9_./-]{1,350}\Z")
MIGRATION_PATH = re.compile(r"^(?:posthog|products|ee|common|flind)/(?:.+/)?migrations/[^/]+\.py$")


class Refusal(Exception):
    pass


def git_env() -> dict[str, str]:
    return {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0"}


def run_git(root: Path, args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], input=input_bytes,
                              capture_output=True, check=False, timeout=90, env=git_env())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refusal("offline_git_unavailable") from exc
    if proc.returncode or len(proc.stdout) > 32 * 1024 * 1024:
        raise Refusal("offline_git_unavailable")
    return proc.stdout


def enumerate_migrations(root: Path, ref: str) -> tuple[str, list[tuple[str, str]], list[str]]:
    if not SAFE_REF.fullmatch(ref) or ref.startswith("-") or ".." in ref.split("/"):
        raise Refusal("invalid_source_ref")
    commit = run_git(root, ["rev-parse", "--verify", ref + "^{commit}"]).decode("ascii").strip()
    if len(commit) not in (40, 64) or not re.fullmatch("[a-f0-9]+", commit):
        raise Refusal("invalid_source_commit")
    listing = run_git(root, ["ls-tree", "-r", "-z", ref, "--", *ROOTS])
    rows: list[tuple[str, str]] = []
    noncanonical: list[str] = []
    for item in listing.split(b"\0"):
        if not item:
            continue
        try:
            meta, name = item.decode("utf-8").split("\t", 1)
            mode, kind, oid = meta.split(" ")
        except (UnicodeDecodeError, ValueError) as exc:
            raise Refusal("invalid_git_tree_record") from exc
        if not MIGRATION_PATH.fullmatch(name):
            continue
        if (mode not in ("100644", "100755") or kind != "blob"
                or len(oid) not in (40, 64)
                or not re.fullmatch("[0-9a-f]+", oid)
                or ".." in Path(name).parts):
            raise Refusal("unsafe_migration_path")
        if not SAFE_FILE.fullmatch(name):
            # A historical copied filename may not be a legal Python module.
            # Report explicitly; never write it as an implicitly safe source.
            noncanonical.append(name)
            continue
        rows.append((oid, name))
        if len(rows) > MAX_FILES:
            raise Refusal("migration_count_exceeds_budget")
    if not rows:
        raise Refusal("no_tracked_migration_sources")
    return commit, rows, noncanonical


def check_blobs(root: Path, rows: list[tuple[str, str]]) -> dict[str, int]:
    unique = list(dict.fromkeys(oid for oid, _ in rows))
    raw = run_git(root, ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                  input_bytes=("\n".join(unique) + "\n").encode("ascii"))
    lines = raw.decode("ascii").splitlines()
    if len(lines) != len(unique):
        raise Refusal("offline_migration_blob_inventory_incomplete")
    sizes: dict[str, int] = {}
    for oid, line in zip(unique, lines, strict=True):
        parts = line.split()
        if len(parts) != 3 or parts[0] != oid or parts[1] != "blob":
            raise Refusal("migration_git_blob_unavailable")
        try:
            size = int(parts[2])
        except ValueError as exc:
            raise Refusal("invalid_git_blob_size") from exc
        if size < 0 or size > MAX_BLOB_BYTES:
            raise Refusal("migration_blob_size_limit")
        sizes[oid] = size
    if sum(sizes[oid] for oid, _ in rows) > MAX_TOTAL_BYTES:
        raise Refusal("migration_total_bytes_limit")
    return sizes


def check_scratch(root: Path) -> None:
    marker = root / MARKER
    if (not (root / ".git").exists() or root.is_symlink()
            or marker.is_symlink() or not marker.is_file()
            or marker.read_text(encoding="utf-8") != MARKER_TEXT):
        raise Refusal("scratch_marker_missing")


def stage(root: Path, ref: str = "HEAD", *, materialize: bool = False) -> dict[str, object]:
    result: dict[str, object] = {
        "phase": "offline-migration-source-hydration",
        "source_ref": ref, "migration_sources_qualified": False,
        "migration_graph_qualified": False, "migrations_applied_qualified": False,
        "rollback_qualified": False, "django_registry_qualified": False,
        "release_qualified": False, "materialize": materialize,
    }
    try:
        if not (root / "pyproject.toml").is_file():
            raise Refusal("flind_source_root_missing")
        commit, rows, noncanonical = enumerate_migrations(root, ref)
        sizes = check_blobs(root, rows)
        by_root: dict[str, int] = {}
        present = 0
        for _, name in rows:
            part = name.split("/", 1)[0]
            by_root[part] = by_root.get(part, 0) + 1
            if (root / name).is_file():
                present += 1
        result.update({
            "source_commit": commit, "tracked_migration_files": len(rows),
            "tracked_migration_candidates": len(rows) + len(noncanonical),
            "noncanonical_migration_paths": noncanonical[:12],
            "noncanonical_migration_count": len(noncanonical),
            "physically_present_before": present,
            "local_git_objects_verified": len(rows),
            "total_bytes": sum(sizes[oid] for oid, _ in rows),
            "by_root": by_root,
        })
        if materialize:
            check_scratch(root)
            # Confirm all pre-existing files match exact Git blobs before writing.
            for oid, name in rows:
                dest = root / name
                if any((root / Path(*Path(name).parts[:depth])).is_symlink()
                       for depth in range(1, len(Path(name).parts) + 1)):
                    raise Refusal("migration_path_symlink_denied")
                if dest.exists():
                    if not dest.is_file():
                        raise Refusal("migration_destination_conflict")
                    # Reject a conflicting pre-existing file *before* any writes.
                    current = dest.read_bytes()
                    header = f"blob {len(current)}\0".encode("ascii")
                    hash_fn = hashlib.sha1 if len(oid) == 40 else hashlib.sha256
                    if hash_fn(header + current).hexdigest() != oid:
                        raise Refusal("migration_destination_conflict")
            proc = subprocess.Popen(
                ["git", "-C", str(root), "cat-file", "--batch"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, env=git_env(),
            )
            written = 0
            try:
                assert proc.stdin is not None and proc.stdout is not None
                for oid, name in rows:
                    proc.stdin.write((oid + "\n").encode("ascii"))
                    proc.stdin.flush()
                    header = proc.stdout.readline().split()
                    if len(header) != 3 or header[0] != oid.encode() or header[1] != b"blob":
                        raise Refusal("migration_blob_read_failed")
                    count = int(header[2])
                    if count != sizes[oid]:
                        raise Refusal("migration_blob_size_changed")
                    data = proc.stdout.read(count)
                    if len(data) != count or proc.stdout.read(1) != b"\n":
                        raise Refusal("migration_blob_frame_invalid")
                    header_bytes = f"blob {len(data)}\0".encode()
                    hash_fn = hashlib.sha1 if len(oid) == 40 else hashlib.sha256
                    if hash_fn(header_bytes + data).hexdigest() != oid:
                        raise Refusal("migration_blob_digest_mismatch")
                    dest = root / name
                    if dest.exists():
                        if dest.read_bytes() != data:
                            raise Refusal("migration_destination_conflict")
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    fd, temp_path = tempfile.mkstemp(prefix=".flind-migration-", dir=dest.parent)
                    try:
                        with os.fdopen(fd, "wb") as stream:
                            stream.write(data)
                        os.replace(temp_path, dest)
                    finally:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                    written += 1
            finally:
                if proc.poll() is None:
                    proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
                for pipe in (proc.stdin, proc.stdout):
                    if pipe is not None:
                        pipe.close()
            result["files_written"] = written
            result["migration_sources_qualified"] = True
        else:
            result["files_written"] = 0
    except (Refusal, OSError, ValueError, UnicodeError) as exc:
        result["blocker"] = str(exc) if isinstance(exc, Refusal) else "migration_preflight_error"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = stage(Path(args.root).resolve(), args.ref, materialize=args.materialize)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Flind migration sources:", "STAGED" if report["migration_sources_qualified"] else "NOT QUALIFIED")
    return 0 if "blocker" not in report else 2


if __name__ == "__main__":
    sys.exit(main())
