#!/usr/bin/env python3
"""Standard-library-only regression tests for the Wave210 Rust preflight."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.qualify_rust_consumer_offline_wave210 import (
    TRACKED,
    locked_registry_inputs,
    qualify,
    source_attestation,
)


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)


class RustConsumerOfflinePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-wave210-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "flind"
        self.root.mkdir()
        self.cargo_home = Path(self.tmp.name) / "cargo"
        self.src = self.cargo_home / "registry/src/index.crates.io-test"
        self.cache = self.cargo_home / "registry/cache/index.crates.io-test"
        self.src.mkdir(parents=True)
        self.cache.mkdir(parents=True)
        lock = self.root / "rust/Cargo.lock"
        lock.parent.mkdir(parents=True)
        checksum = hashlib.sha256(b"synthetic fixture; no execution").hexdigest()
        lock.write_text(
            'version = 3\n'
            '[[package]]\nname = "ahash"\nversion = "0.8.12"\n'
            'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
            f'checksum = "{checksum}"\n'
            '[[package]]\nname = "addr2line"\nversion = "0.25.1"\n'
            'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
            f'checksum = "{checksum}"\n',
            encoding="utf8",
        )
        for path in TRACKED:
            p = self.root / path
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("// synthetic fixture\n", encoding="utf8")
        git(self.root, "init", "-q")
        git(self.root, "add", ".")
        git(self.root, "-c", "user.name=Flind fixture",
            "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")

    def test_unpacked_sources_cannot_substitute_for_missing_archives(self) -> None:
        for name in ("ahash-0.8.12", "addr2line-0.25.1"):
            p = self.src / name
            p.mkdir()
            (p / "Cargo.toml").write_text("[package]\nname = 'fixture'\n", encoding="utf8")
        report = locked_registry_inputs(self.root / "rust/Cargo.lock", self.cargo_home)
        self.assertEqual(report["locked_registry_packages"], 2)
        self.assertEqual(report["unpacked_source_packages_present"], 2)
        self.assertEqual(report["offline_archives_missing"], 2)
        self.assertEqual(report["unverified_unpacked_sources"], 2)
        self.assertFalse(report["locked_archive_closure_available"])

    def test_exact_locked_cache_inputs_detect_absent_crate(self) -> None:
        (self.cache / "ahash-0.8.12.crate").write_bytes(b"synthetic fixture; no execution")
        report = locked_registry_inputs(self.root / "rust/Cargo.lock", self.cargo_home)
        self.assertEqual(report["offline_archives_present"], 1)
        self.assertEqual(report["missing_archive_examples"], ["addr2line-0.25.1"])
        self.assertEqual(report["unpacked_sources_missing"], 2)

    def test_corrupt_same_named_archive_does_not_count(self) -> None:
        (self.cache / "ahash-0.8.12.crate").write_bytes(b"wrong checksum")
        (self.cache / "addr2line-0.25.1.crate").write_bytes(b"synthetic fixture; no execution")
        report = locked_registry_inputs(self.root / "rust/Cargo.lock", self.cargo_home)
        self.assertEqual(report["offline_archives_present"], 1)
        self.assertEqual(report["offline_archives_checksum_invalid"], 1)
        self.assertEqual(report["invalid_archive_examples"], ["ahash-0.8.12"])
        self.assertFalse(report["locked_archive_closure_available"])

    def test_complete_archive_fixture_can_pass_only_with_attestation(self) -> None:
        for name in ("ahash-0.8.12", "addr2line-0.25.1"):
            (self.cache / (name + ".crate")).write_bytes(b"synthetic fixture; no execution")
        with patch(
            "tools.flind.qualify_rust_consumer_offline_wave210.metadata_check",
            return_value={"cargo_offline_locked_metadata_pass": True,
                          "metadata_return_code": 0},
        ):
            report = qualify(self.root, self.cargo_home)
        self.assertTrue(report["offline_native_consumer_test_preflight_pass"])
        self.assertTrue(report["tracked_sources_match_head"])
        self.assertFalse(report["native_rust_consumer_compiled"])
        self.assertFalse(report["native_rust_grpc_tests_executed"])
        self.assertFalse(report["release_qualified"])
        (self.root / "rust/ingestion-consumer/src/consumer.rs").write_text(
            "changed without commit\n", encoding="utf8"
        )
        with patch(
            "tools.flind.qualify_rust_consumer_offline_wave210.metadata_check",
            return_value={"cargo_offline_locked_metadata_pass": True,
                          "metadata_return_code": 0},
        ):
            dirty = qualify(self.root, self.cargo_home)
        self.assertFalse(dirty["tracked_sources_match_head"])
        self.assertFalse(dirty["offline_native_consumer_test_preflight_pass"])

    def test_unavailable_git_repo_fails_closed(self) -> None:
        report = qualify(self.cargo_home, self.cargo_home, run_metadata=False)
        self.assertFalse(report["offline_native_consumer_test_preflight_pass"])
        self.assertFalse(report["release_qualified"])


if __name__ == "__main__":
    unittest.main()
