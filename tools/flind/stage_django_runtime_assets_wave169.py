#!/usr/bin/env python3
"""Verify and stage first-party Flind runtime assets into a marked scratch folder.

No Git lazy fetching, no source-tree mutations, no automatic deployment.
An optional externally supplied seed must match the tracked Git blob digest.
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

DEFAULT_ASSETS = (
    "products/growth/backend/enrichment/scoring_formula.hog",
    "products/alerts/backend/logic/destination_stock_inputs.json",
)
MARKER = ".flind-runtime-scratch-v1"
MARKER_CONTENT = "FLIND_RUNTIME_ASSETS_SCRATCH_V1\n"
ROOTS = frozenset(("posthog", "products", "ee", "common", "flind"))
SUFFIXES = frozenset((".hog", ".json", ".yaml", ".yml", ".toml", ".sql", ".graphql", ".proto", ".csv"))
SAFE_REF = re.compile(r"[A-Za-z0-9_./-]{1,128}\Z")
MAX_ASSETS = 24
MAX_ASSET_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
SAFE_ASSET = re.compile(r"[A-Za-z0-9_./-]{1,350}\Z")
WINDOWS_RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.IGNORECASE)


def is_link(path: Path) -> bool:
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


class StagingError(Exception):
    """Expected and sanitized offline-staging refusal."""


def checked_asset(value: str) -> str:
    candidate = Path(value)
    if (not SAFE_ASSET.fullmatch(value) or "//" in value
            or candidate.is_absolute() or ".." in candidate.parts
            or len(candidate.parts) < 2 or candidate.parts[0] not in ROOTS
            or any(WINDOWS_RESERVED.fullmatch(part) for part in candidate.parts)
            or candidate.suffix.lower() not in SUFFIXES):
        raise StagingError("invalid_asset_path")
    return candidate.as_posix()


def git(repo: Path, args: list[str], input_data: bytes | None = None) -> bytes:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_OPTIONAL_LOCKS": "0"}
    try:
        cp = subprocess.run(["git", "-C", str(repo), *args], input=input_data,
                            capture_output=True, check=False, timeout=30, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StagingError("offline_git_unavailable") from exc
    if cp.returncode != 0:
        raise StagingError("offline_git_unavailable")
    return cp.stdout


def tracked_blobs(repo: Path, ref: str, paths: list[str]) -> dict[str, str]:
    if not SAFE_REF.fullmatch(ref) or ref.startswith("-") or ".." in ref.split("/"):
        raise StagingError("invalid_source_ref")
    raw = git(repo, ["ls-tree", "-z", ref, "--", *paths])
    result = {}
    for record in raw.split(b"\x00"):
        if not record:
            continue
        try:
            meta, name = record.decode("utf-8").split("\t", 1)
            mode, kind, oid = meta.split(" ")
        except (UnicodeDecodeError, ValueError) as exc:
            raise StagingError("invalid_git_entry") from exc
        if (mode not in ("100644", "100755") or kind != "blob"
                or len(oid) not in (40, 64) or any(c not in "0123456789abcdef" for c in oid)):
            raise StagingError("invalid_git_entry")
        if name in paths:
            result[name] = oid
    return result


def hash_blob(data: bytes, oid: str) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    algorithm = hashlib.sha1 if len(oid) == 40 else hashlib.sha256
    return algorithm(header + data).hexdigest()


def read_verified(repo: Path, oid: str, name: str, seed: Path | None) -> tuple[bytes, str]:
    # Refuse to read unexpectedly large Git objects into memory.
    origin = "local_git"
    try:
        size = int(git(repo, ["cat-file", "-s", oid]).decode("ascii").strip())
        if size < 0 or size > MAX_ASSET_BYTES:
            raise StagingError("asset_size_budget_exceeded")
        data = git(repo, ["cat-file", "blob", oid])
    except (StagingError, ValueError, UnicodeDecodeError):
        if seed is None:
            raise StagingError("local_blob_unavailable") from None
        origin = "verified_seed"
        candidate = seed / name
        if is_link(candidate) or not candidate.is_file():
            raise StagingError("verified_seed_unavailable")
        try:
            candidate.resolve().relative_to(seed.resolve())
        except ValueError as exc:
            raise StagingError("unsafe_seed_path") from exc
        if candidate.stat().st_size > MAX_ASSET_BYTES:
            raise StagingError("asset_size_budget_exceeded")
        data = candidate.read_bytes()
    if len(data) > MAX_ASSET_BYTES:
        raise StagingError("asset_size_budget_exceeded")
    if hash_blob(data, oid) != oid:
        raise StagingError("asset_digest_mismatch")
    return data, origin


def assert_scratch(repo: Path, target: Path) -> None:
    if is_link(target) or not target.is_dir():
        raise StagingError("scratch_target_not_directory")
    source_real, target_real = repo.resolve(), target.resolve()
    if (source_real == target_real or source_real in target_real.parents
            or target_real in source_real.parents):
        raise StagingError("scratch_overlaps_repository")
    marker = target / MARKER
    if is_link(marker) or not marker.is_file() or marker.read_text() != MARKER_CONTENT:
        raise StagingError("scratch_marker_missing")


def safely_dest(target: Path, name: str) -> Path:
    dest = target / name
    if any(is_link(p) for p in (dest, *list(dest.parents)[:-1])):
        raise StagingError("scratch_symlink_denied")
    try:
        dest.resolve().relative_to(target.resolve())
    except ValueError as exc:
        raise StagingError("scratch_escape_denied") from exc
    return dest


def stage(repo: Path, target: Path, paths: list[str], *, ref: str = "HEAD",
          seed: Path | None = None, materialize: bool = False) -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "verified-offline-scratch-resource-staging", "source_ref": ref,
        "materialize": materialize, "files_verified": 0, "files_written": 0,
        "resource_staging_qualified": False, "django_registry_qualified": False,
        "migrations_qualified": False, "release_qualified": False,
    }
    try:
        if not paths or len(paths) > MAX_ASSETS:
            raise StagingError("asset_count_budget_exceeded")
        validated = [checked_asset(p) for p in paths]
        if len(set(validated)) != len(validated):
            raise StagingError("duplicate_asset")
        assert_scratch(repo, target)
        oids = tracked_blobs(repo, ref, validated)
        source_commit = git(repo, ["rev-parse", "--verify", ref + "^{commit}"]).decode("ascii").strip()
        if len(source_commit) not in (40, 64) or any(c not in "0123456789abcdef" for c in source_commit):
            raise StagingError("invalid_resolved_source_commit")
        if set(oids) != set(validated):
            raise StagingError("asset_not_tracked_at_ref")
        pending: list[tuple[Path, bytes]] = []
        receipts: list[dict[str, object]] = []
        total = 0
        for name in validated:
            destination = safely_dest(target, name)
            data, origin = read_verified(repo, oids[name], name, seed)
            receipts.append({
                "path": name,
                "git_blob_oid": oids[name],
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
                "verified_from": origin,
            })
            total += len(data)
            if total > MAX_TOTAL_BYTES:
                raise StagingError("total_asset_budget_exceeded")
            if destination.exists():
                if not destination.is_file() or destination.read_bytes() != data:
                    raise StagingError("existing_scratch_asset_conflicts")
            else:
                pending.append((destination, data))
        report["files_verified"] = len(validated)
        if materialize:
            for destination, data in pending:
                destination.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(prefix=".flind-stage-", dir=destination.parent)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(data)
                    os.replace(tmp, destination)
                finally:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
            report["files_written"] = len(pending)
        report["verified_assets"] = validated
        report["source_commit"] = source_commit
        report["file_receipts"] = receipts
        report["total_verified_bytes"] = total
        report["resource_staging_qualified"] = materialize
    except (StagingError, OSError, UnicodeError) as exc:
        report["blocker"] = str(exc) if isinstance(exc, StagingError) else "filesystem_unavailable"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--scratch", required=True, help="Existing separate marked scratch directory")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--seed", help="Optional offline candidate files, checked against Git OIDs")
    parser.add_argument("--asset", action="append")
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = stage(Path(args.repo), Path(args.scratch),
                   args.asset if args.asset else list(DEFAULT_ASSETS),
                   ref=args.ref, seed=Path(args.seed) if args.seed else None,
                   materialize=args.materialize)
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print("Flind verified scratch assets:",
              "STAGED" if result["resource_staging_qualified"] else
              "VERIFIED" if result["files_verified"] else "BLOCKED")
    return 0 if result["files_verified"] and "blocker" not in result else 2


if __name__ == "__main__":
    sys.exit(main())
