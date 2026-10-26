"""Wave121 admission and exact evidence boundaries for original Rust Kafka/gRPC tests."""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_original_rust_grpc_kafka_wave121 as q


class RustOriginalGrpcKafkaWave121(unittest.TestCase):
    def test_exact_original_rust_test_names_are_allowlisted(self):
        self.assertEqual(len(q.TESTS), 3)
        for name in q.TESTS:
            self.assertRegex(name, r"^[a-z0-9_]+$")
        self.assertIn("the_committed_offset_is_the_ledger_frontier", q.TESTS)
        self.assertIn("a_partial_ack_redelivers_only_the_unfinished_messages", q.TESTS)
        self.assertIn("consumer_crash_before_commit_redelivers_without_loss", q.TESTS)

    def test_broker_not_loopback_refused_before_git(self):
        with patch.object(q, "git") as g:
            report = q.smoke("kafka.example.com:9092")
            g.assert_not_called()
        self.assertFalse(report["first_party_rust_grpc_kafka_e2e"])
        self.assertFalse(report["release_qualified"])

    def test_unknown_case_refused_without_subprocess_or_git(self):
        with patch.object(q, "git") as g:
            report = q.smoke("127.0.0.1:19092", tests=("arbitrary_unapproved_case",))
            g.assert_not_called()
        self.assertIn("Unapproved", report["blocker"])
        self.assertFalse(report["first_party_rust_grpc_kafka_e2e"])

    def test_duplicate_case_selection_refused(self):
        with patch.object(q, "git") as g:
            result = q.smoke("127.0.0.1:19092", tests=(q.TESTS[0], q.TESTS[0]))
            g.assert_not_called()
        self.assertFalse(result["first_party_rust_grpc_kafka_e2e"])

    def test_no_fake_release_claims(self):
        with patch.object(q, "FULL", Path("/nonexistent-flind-wave121-test-checkout")):
            result = q.smoke("127.0.0.1:19092")
        self.assertFalse(result["first_party_rust_grpc_kafka_e2e"])
        for field in (
            "production_node_worker_qualified",
            "product_clickhouse_schema_qualified",
            "tenant_query_api_qualified",
            "browser_dashboard_qualified",
            "release_qualified",
        ):
            self.assertFalse(result[field])

    def test_exact_first_party_test_location_and_no_download(self):
        content = (q.ROOT / "tools/flind/qualify_original_rust_grpc_kafka_wave121.py").read_text()
        for assertion in (
            '"cargo", "test", "--locked", "--offline"',
            '"--test", "e2e_integration_test", case',
            '"--", "--exact", "--nocapture"',
            '"full_checkout_original_source_restored"',
            'os.killpg(process.pid, signal.SIGTERM)',
            'CARGO_NET_OFFLINE',
            'production_nodejs_ingestion_worker_qualified": False',
        ):
            self.assertIn(assertion, content)

    def test_original_test_git_tree_provenance_and_recovery(self):
        if not q.FULL.is_dir():
            self.skipTest("Temporary full checkout unavailable")
        self.assertEqual(
            q.git(q.FULL, "rev-parse", "HEAD:" + q.TEST_SOURCE),
            q.git(q.ROOT, "rev-parse", "HEAD:" + q.TEST_SOURCE),
        )
        self.assertEqual(q.git(q.FULL, "status", "--porcelain", "--", q.TEST_SOURCE), "")


if __name__ == "__main__":
    unittest.main()
