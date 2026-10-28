#!/usr/bin/env python3
"""Standard-library-only tests for Wave212 real-Kafka Rust qualification."""
from __future__ import annotations

import hashlib
import socket
from pathlib import Path
import tempfile
import unittest

from tools.flind.qualify_original_rust_kafka_wave212 import (
    MARKER, TESTS, broker_cleanup_verified, run_original_tests, verify_runtime,
)


class OriginalRustKafkaQualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="flind-wave212-regression-")
        self.addCleanup(temp.cleanup)
        self.runtime = Path(temp.name) / "runtime"
        self.runtime.mkdir()
        (self.runtime / ".flind-wave212-owner").write_text(MARKER, encoding="utf8")
        (self.runtime / "kafka/bin").mkdir(parents=True)
        (self.runtime / "kafka/bin/kafka-server-start.sh").write_text(
            "#!/bin/sh\n", encoding="utf8"
        )
        self.payload = self.runtime / "kafka.tgz"
        self.payload.write_bytes(b"test-only synthetic archive")
        digest = hashlib.sha512(self.payload.read_bytes()).hexdigest().upper()
        (self.runtime / "kafka.sha512").write_text(
            "kafka_2.13-4.3.1.tgz: " + digest + "\n", encoding="utf8"
        )

    def test_marker_and_checksum_are_required(self) -> None:
        self.assertTrue(verify_runtime(self.runtime))
        (self.runtime / ".flind-wave212-owner").write_text("unowned\n", encoding="utf8")
        self.assertFalse(verify_runtime(self.runtime))

    def test_corrupt_archive_fails_closed(self) -> None:
        self.payload.write_bytes(b"corrupted archive")
        self.assertFalse(verify_runtime(self.runtime))

    def test_symlink_runtime_is_not_followed(self) -> None:
        alias = self.runtime.parent / "alias"
        alias.symlink_to(self.runtime, target_is_directory=True)
        self.assertFalse(verify_runtime(alias))

    def test_rust_tests_are_the_original_commit_and_replay_cases(self) -> None:
        self.assertEqual(len(TESTS), 3)
        self.assertEqual(len(set(TESTS)), 3)
        self.assertIn("the_committed_offset_is_the_ledger_frontier", TESTS)
        self.assertIn("consumer_crash_before_commit_redelivers_without_loss", TESTS)
        self.assertIn("a_partial_ack_redelivers_only_the_unfinished_messages", TESTS)

    def test_isolated_kafka_cleanup_rejects_stale_data(self) -> None:
        storage = self.runtime / "tmp"
        storage.mkdir()
        stale = storage / "flind-kafka-stale"
        stale.mkdir()
        self.assertFalse(broker_cleanup_verified(storage, timeout_seconds=0.05))
        stale.rmdir()
        self.assertTrue(broker_cleanup_verified(storage))

    def test_active_listener_cannot_be_mistaken_for_cleanup(self) -> None:
        storage = self.runtime / "tmp"
        storage.mkdir()
        with socket.socket() as held:
            held.bind(("127.0.0.1", 0))
            held.listen()
            port = held.getsockname()[1]
            self.assertFalse(
                broker_cleanup_verified(storage, port=port, timeout_seconds=0.05)
            )
        self.assertTrue(
            broker_cleanup_verified(storage, port=port, timeout_seconds=0.05)
        )

    def test_missing_owned_native_build_cannot_claim_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = run_original_tests(Path(temp), Path(temp))
        self.assertFalse(result["passed"])
        self.assertIn("blocker", result)


if __name__ == "__main__":
    unittest.main()
