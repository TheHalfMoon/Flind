#!/usr/bin/env python3
"""Wave210: audited, read-only preflight for native Flind Rust consumer tests.

Checks first-party Git provenance and the locked Cargo registry inputs without
downloading dependencies, mutating Cargo caches, or claiming an unrun test.
Python 3.11+; no third-party dependencies required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
TRACKED = (
    "rust/Cargo.lock",
    "rust/ingestion-consumer/Cargo.toml",
    "rust/ingestion-consumer/src/consumer.rs",
    "rust/ingestion-consumer/src/grpc_transport.rs",
    "rust/ingestion-consumer/tests/grpc_transport_test.rs",
)
MAX_SAMPLES = 12


def locked_registry_inputs(lockfile: Path, cargo_home: Path) -> dict:
    """List missing offline Cargo package archives and unpacked source trees.

    An unpacked source without a matching .crate archive (or authentic vendor
    checksum metadata) is *not* sufficient for an ordinary offline Cargo build.
    This intentionally reports the conservative full workspace lockfile closure.
    """
    content = tomllib.loads(lockfile.read_text(encoding="utf8"))
    packages = content.get("package")
    if not isinstance(packages, list):
        raise ValueError("Cargo.lock has no package list")
    sources = sorted((cargo_home / "registry" / "src").glob("*"))
    caches = sorted((cargo_home / "registry" / "cache").glob("*"))
    locked = []
    for entry in packages:
        if not isinstance(entry, dict):
            raise ValueError("malformed Cargo.lock package")
        origin = entry.get("source", "")
        if not isinstance(origin, str):
            raise ValueError("invalid Cargo.lock source")
        if origin.startswith("registry+"):
            name = entry.get("name")
            version = entry.get("version")
            checksum = entry.get("checksum")
            if not isinstance(name, str) or not isinstance(version, str):
                raise ValueError("registry package lacks name/version")
            if not isinstance(checksum, str) or len(checksum) != 64:
                raise ValueError("registry package lacks SHA-256 lockfile checksum")
            locked.append((name, version, checksum))
    if not locked:
        raise ValueError("Cargo.lock contains no registry packages")

    missing_archives = []
    invalid_archives = []
    verified_archives = 0
    missing_sources = []
    unverified_extracted = []
    for name, version, checksum in locked:
        filename = f"{name}-{version}"
        archive = filename + ".crate"
        candidates = [cache / archive for cache in caches if (cache / archive).is_file()]
        if not candidates:
            missing_archives.append(filename)
        else:
            # A same-named or corrupted archive cannot satisfy Cargo.lock.
            # Inspect the cached bytes; never repair caches or fetch packages.
            verified = False
            for candidate in candidates:
                with candidate.open("rb") as handle:
                    if hashlib.file_digest(handle, "sha256").hexdigest() == checksum:
                        verified = True
                        break
            if verified:
                verified_archives += 1
            else:
                invalid_archives.append(filename)
        extracted = [root / filename for root in sources if (root / filename / "Cargo.toml").is_file()]
        if not extracted:
            missing_sources.append(filename)
        elif not any((folder / ".cargo-checksum.json").is_file() for folder in extracted):
            unverified_extracted.append(filename)

    return {
        "locked_registry_packages": len(locked),
        "offline_archives_present": verified_archives,
        "offline_archives_missing": len(missing_archives),
        "offline_archives_checksum_invalid": len(invalid_archives),
        "unpacked_source_packages_present": len(locked) - len(missing_sources),
        "unpacked_sources_missing": len(missing_sources),
        "unverified_unpacked_sources": len(unverified_extracted),
        "missing_archive_examples": missing_archives[:MAX_SAMPLES],
        "invalid_archive_examples": invalid_archives[:MAX_SAMPLES],
        "missing_source_examples": missing_sources[:MAX_SAMPLES],
        "unverified_unpacked_examples": unverified_extracted[:MAX_SAMPLES],
        "locked_archive_closure_available": not missing_archives and not invalid_archives,
    }


def source_attestation(root: Path) -> dict:
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    if revision.returncode or len(revision.stdout.strip()) != 40:
        raise ValueError("Flind Git HEAD unavailable")
    is_tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", *TRACKED],
        capture_output=True, text=True, timeout=15, check=False,
    )
    clean = subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", *TRACKED],
        capture_output=True, timeout=45, check=False,
    )
    return {
        "head_sha": revision.stdout.strip(),
        "tracked_first_party_sources": is_tracked.returncode == 0,
        "tracked_sources_match_head": clean.returncode == 0,
    }


def metadata_check(root: Path) -> dict:
    env = {**os.environ, "CARGO_NET_OFFLINE": "true"}
    result = subprocess.run(
        ["cargo", "metadata", "--offline", "--locked", "--no-deps", "--format-version", "1"],
        cwd=root / "rust", env=env,
        capture_output=True, timeout=45, check=False,
    )
    return {
        "cargo_offline_locked_metadata_pass": result.returncode == 0,
        "metadata_return_code": result.returncode,
    }


def qualify(root: Path, cargo_home: Path, *, run_metadata: bool = True) -> dict:
    root = root.resolve()
    cargo_home = cargo_home.expanduser().resolve()
    base = {
        "phase": "wave210_firstparty_rust_consumer_offline_preflight",
        "read_only_no_download": True,
        "native_rust_consumer_compiled": False,
        "native_rust_grpc_tests_executed": False,
        "native_rust_kafka_node_joined_clickhouse_e2e": False,
        "full_native_jest_qualified": False,
        "release_qualified": False,
    }
    try:
        provenance = source_attestation(root)
        inputs = locked_registry_inputs(root / "rust/Cargo.lock", cargo_home)
        metadata = metadata_check(root) if run_metadata else {
            "cargo_offline_locked_metadata_pass": False,
            "metadata_return_code": None,
        }
        output = {**base, **provenance, **inputs, **metadata}
        output["offline_native_consumer_test_preflight_pass"] = all((
            output["tracked_first_party_sources"],
            output["tracked_sources_match_head"],
            output["cargo_offline_locked_metadata_pass"],
            output["locked_archive_closure_available"],
        ))
        if not output["offline_native_consumer_test_preflight_pass"]:
            output["blocker"] = (
                "Offline Cargo closure or source provenance incomplete; "
                "native Rust test was NOT executed"
            )
        return output
    except (ValueError, FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        return {
            **base,
            "offline_native_consumer_test_preflight_pass": False,
            "blocker": type(exc).__name__,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--cargo-home", type=Path,
                        default=Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo")))
    args = parser.parse_args()
    report = qualify(args.repo, args.cargo_home)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["offline_native_consumer_test_preflight_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
