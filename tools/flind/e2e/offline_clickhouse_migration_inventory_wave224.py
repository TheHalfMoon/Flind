#!/usr/bin/env python3
"""Read-only, Git-backed inventory of the ORIGINAL Flind ClickHouse migrations.

Do not import migration modules or invoke migrate_clickhouse --plan: the latter
creates a database and/or migration tracking tables before listing its plan.
This is source provenance only, NEVER live schema or release qualification.
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

MIGRATION_ROOT = "posthog/clickhouse/migrations/"
CANONICAL = re.compile(r"^posthog/clickhouse/migrations/(\d{4}_[a-z0-9_]+)\.py$")
REF = re.compile(r"(?:HEAD|[a-f0-9]{40}|refs/heads/[a-z0-9_/-]{1,96})\Z")
MAX_LIST_BYTES = 2 * 1024 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 48 * 1024 * 1024


def offline_git_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }


def git(root: Path, arguments: list[str], *, input_bytes: bytes | None = None) -> bytes:
    if arguments[0] not in {"rev-parse", "ls-tree", "cat-file"}:
        raise ValueError("not a read-only Git operation")
    result = subprocess.run(
        ["git", "-C", str(root), *arguments], input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=30, check=False, env=offline_git_env(),
    )
    if result.returncode:
        raise RuntimeError("offline Git source query failed")
    if len(result.stdout) > MAX_LIST_BYTES:
        raise ValueError("offline Git output exceeds size budget")
    return result.stdout


def audit(root: Path, ref: str = "HEAD") -> dict[str, object]:
    receipt: dict[str, object] = {
        "phase": "wave224_offline_clickhouse_migration_source_inventory",
        "source_inventory_qualified": False,
        "clickhouse_schema_qualified": False,
        "migrations_applied_qualified": False,
        "native_ingestion_e2e_qualified": False,
        "release_qualified": False,
    }
    try:
        root = root.resolve(strict=True)
        if not REF.fullmatch(ref) or ref.startswith("-"):
            raise ValueError("unsafe source ref")
        if not (root / ".git").exists() or not (root / "pyproject.toml").is_file():
            raise ValueError("Flind source checkout unavailable")
        top = git(root, ["rev-parse", "--show-toplevel"]).decode("utf-8").strip()
        if Path(top).resolve() != root:
            raise ValueError("source is not Git repository root")
        sha = git(root, ["rev-parse", "--verify", f"{ref}^{{commit}}"]).decode("ascii").strip()
        if not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError("invalid immutable Git commit")
        listing = git(root, ["ls-tree", "-r", "-z", "--long", sha, "--", MIGRATION_ROOT])
        canonical: list[tuple[str, str, int]] = []
        noncanonical: list[str] = []
        noncanonical_blobs: list[tuple[str, str, int]] = []
        sql_assets: list[tuple[str, str, int]] = []
        total_bytes = 0
        sql_asset_bytes = 0
        for record in listing.split(b"\0"):
            if not record:
                continue
            meta, tab, raw_path = record.partition(b"\t")
            if tab != b"\t":
                raise ValueError("malformed Git tree entry")
            path = raw_path.decode("utf-8", errors="strict")
            if not path.startswith(MIGRATION_ROOT) or ".." in Path(path).parts:
                raise ValueError("unsafe source path")
            if path == MIGRATION_ROOT + "__init__.py":
                continue
            if not (path.endswith(".py") or path.endswith(".sql")):
                continue
            fields = meta.split()
            if len(fields) != 4:
                raise ValueError("malformed Git tree metadata")
            mode, typ, object_id, size_bytes = fields
            if mode != b"100644" and mode != b"100755":
                raise ValueError("migration module is not a regular tracked file")
            if typ != b"blob" or not re.fullmatch(rb"[a-f0-9]{40}", object_id):
                raise ValueError("untrusted migration object")
            size = int(size_bytes)
            if size < 0 or size > MAX_SOURCE_BYTES:
                raise ValueError("migration module exceeds source size limit")
            total_bytes += size
            if total_bytes > MAX_TOTAL_SOURCE_BYTES:
                raise ValueError("total migration sources exceed size limit")
            if path.endswith(".sql"):
                sql_assets.append((path, object_id.decode("ascii"), size))
                sql_asset_bytes += size
            elif CANONICAL.fullmatch(path):
                canonical.append((path, object_id.decode("ascii"), size))
            else:
                noncanonical.append(path)
                noncanonical_blobs.append((path, object_id.decode("ascii"), size))
        if not canonical:
            raise ValueError("original ClickHouse migrations not found")
        # Verify migration Python modules AND original SQL assets (including
        # nested sql/0238/*.sql). SQL is executed by migration modules and a
        # Python-only inventory would miss changes to the effective DDL source.
        sources = canonical + noncanonical_blobs + sql_assets
        objects = [obj_id for _path, obj_id, _size in sources]
        response = git(root, ["cat-file", "--batch-check"], input_bytes=("\n".join(objects) + "\n").encode())
        reported = response.decode("ascii").splitlines()
        if len(reported) != len(sources):
            raise ValueError("incomplete local Git blob inventory")
        for (_path, expected, expected_size), line in zip(sources, reported, strict=True):
            parts = line.split(" ")
            if len(parts) != 3 or parts[0] != expected or parts[1] != "blob":
                raise ValueError("missing original Git migration blob")
            size = int(parts[2])
            if size != expected_size:
                raise ValueError("mismatched original Git migration blob size")
        # Fingerprint all attested migration Python and SQL sources. Changes
        # to historical Python files or original SQL DDL alter this manifest.
        digest = hashlib.sha256()
        canonical.sort(key=lambda item: item[0])
        for path, object_id, size in sorted(sources, key=lambda item: item[0]):
            digest.update(path.encode("utf-8") + b"\0" + object_id.encode("ascii") + b"\0")
        receipt.update({
            "source_commit": sha,
            "canonical_migration_modules": len(canonical),
            "source_file_bytes": total_bytes,
            "sql_asset_count": len(sql_assets),
            "sql_asset_bytes": sql_asset_bytes,
            "sql_asset_paths": sorted(path for path, _oid, _size in sql_assets),
            "noncanonical_module_paths": sorted(noncanonical),
            "noncanonical_module_count": len(noncanonical),
            "first_module": canonical[0][0],
            "last_module": canonical[-1][0],
            "module_manifest_sha256": digest.hexdigest(),
            "source_inventory_qualified": True,
            "scope": "Git Python migration and SQL asset blobs; no imports or DB connections",
        })
    except (OSError, RuntimeError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
        receipt["blocker"] = type(exc).__name__
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    receipt = audit(args.root, args.ref)
    if args.json:
        print(json.dumps(receipt, sort_keys=True, indent=2))
    else:
        print("Flind ClickHouse original source inventory:",
              "PASS" if receipt["source_inventory_qualified"] else "BLOCKED")
        print("ClickHouse schemas, ingestion and release: NOT QUALIFIED")
    return 0 if receipt["source_inventory_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
