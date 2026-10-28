#!/usr/bin/env python3
"""Dependency-free tests of Wave211 Rust integration qualifier fail-closed gates."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.flind.qualify_native_rust_grpc_transport_wave211 import (
    MARKER, OWNER, parse_test_result, target_safely_owned,
)


class NativeRustGrpcQualifierTests(unittest.TestCase):
    def test_real_rust_harness_success_line(self) -> None:
        output = (
            "running 20 tests\n"
            "test a::b ... ok\n"
            "test result: ok. 20 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out\n"
        )
        self.assertEqual(parse_test_result(output), (20, 0))

    def test_failing_or_missing_rust_report_cannot_pass(self) -> None:
        self.assertEqual(
            parse_test_result("test result: FAILED. 1 passed; 2 failed; 0 ignored"),
            (1, 2),
        )
        self.assertEqual(parse_test_result("Compiling something\nerror: missing dependency"), (0, -1))
        self.assertEqual(parse_test_result(
            "test result: ok. 20 passed; 0 failed;\ntest result: ok. 20 passed; 0 failed;"
        ), (0, -1))

    def test_only_owned_and_sibling_target_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flind-wave211-safe-") as temp:
            base = Path(temp)
            root = base / "Flind-wave211"
            root.mkdir()
            target = base / "Flind-wave211-rust-target"
            self.assertTrue(target_safely_owned(root, target))
            self.assertEqual((target / OWNER).read_text(encoding="utf8"), MARKER)
            (target / OWNER).write_text("OTHER PROJECT\n", encoding="utf8")
            self.assertFalse(target_safely_owned(root, target))
            self.assertFalse(target_safely_owned(root, base / "foreign-target"))

    def test_symlinked_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flind-wave211-symlink-") as temp:
            base = Path(temp)
            root = base / "Flind-wave211"
            root.mkdir()
            foreign = base / "foreign"
            foreign.mkdir()
            (foreign / OWNER).write_text(MARKER, encoding="utf8")
            link = base / "Flind-wave211-rust-target"
            link.symlink_to(foreign, target_is_directory=True)
            self.assertFalse(target_safely_owned(root, link))


if __name__ == "__main__":
    unittest.main()
