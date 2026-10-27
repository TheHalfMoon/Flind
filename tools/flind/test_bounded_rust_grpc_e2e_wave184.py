"""Wave184 test harness safety and source-integrity checks without services."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_bounded_rust_grpc_e2e_wave184 as w


class OriginalRustE2EAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-rust184-", dir="/private/tmp")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self):
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.repo), "-c", "user.name=Flind Tests",
            "-c", "user.email=flind@invalid.example",
            "commit", "-qm", "synthetic Rust source fixture",
        ], check=True)

    def test_original_ledger_name_fixed_and_release_false(self):
        self.assertEqual(w.CASE, "the_committed_offset_is_the_ledger_frontier")
        self.assertIn("e2e_integration_test.rs", w.FILES[-1])
        self.assertGreaterEqual(w.MIN_FREE_BYTES, 3 * 1024**3)
        self.assertLessEqual(w.MAX_COMPILE_SECONDS, 180)

    def test_only_nine_exact_original_rust_scenarios_are_allowed(self):
        self.assertEqual(w.CASES, (
            "the_committed_offset_is_the_ledger_frontier",
            "a_partial_ack_redelivers_only_the_unfinished_messages",
            "consumer_crash_before_commit_redelivers_without_loss",
            "lost_ack_after_processing_replays_without_loss",
            "poison_batch_fails_safely_without_committing",
            "partial_acceptance_fails_the_batch_without_commit",
            "failing_worker_triggers_rerouting",
            "drainer_crash_mid_drain_replays_to_survivor_in_order",
            "nacking_worker_fences_worker_stream_and_reroutes_in_order",
        ))
        for invalid in ("all", "cargo clean", "--help", "", "unlisted_test"):
            with patch.object(w, "source_ready") as source, patch.object(
                w.subprocess, "Popen"
            ) as command:
                result = w.native_single_rust_test(
                    "127.0.0.1:19092", self.root,
                    reference=self.repo, full=self.root, case=invalid
                )
            self.assertEqual(result["blocker"], "unapproved_rust_integration_case")
            self.assertFalse(result["rust_original_kafka_grpc_ledger_test_pass"])
            self.assertFalse(result["release_qualified"])
            source.assert_not_called()
            command.assert_not_called()

    def test_verified_git_blob_matches_locally_tracked_source(self):
        target = self.repo / "src" / "main.rs"
        target.parent.mkdir()
        target.write_text("fn main() {}\n")
        self.commit()
        self.assertEqual(w.verified_blob(self.repo, "src/main.rs"), b"fn main() {}\n")

    def test_missing_blob_refused_offline(self):
        (self.repo / "README.txt").write_text("Flind synthetic only\n")
        self.commit()
        with self.assertRaises(w.RustBlocked):
            w.verified_blob(self.repo, "src/nonexistent.rs")

    def test_loopback_is_only_allowed_kafka_broker(self):
        with patch.object(w, "offline_git") as git:
            for host in ("kafka.example.com:9092", "0.0.0.0:9092", "localhost:9092",
                         "127.0.0.1:bad", "", "127.0.0.1:9092; cmd"):
                self.assertFalse(w.source_ready(self.repo, self.repo, host))
            git.assert_not_called()

    def test_full_and_reference_checkout_cannot_be_same(self):
        self.assertFalse(w.source_ready(self.repo, self.repo, "127.0.0.1:19092"))

    def test_invalid_broker_never_runs_cargo(self):
        with patch.object(w, "source_ready", return_value=False), patch.object(
            w.subprocess, "Popen"
        ) as cargo:
            report = w.native_single_rust_test(
                "kafka.example.com:9092", self.root,
                reference=self.repo, full=self.root
            )
        cargo.assert_not_called()
        self.assertFalse(report["rust_original_kafka_grpc_ledger_test_pass"])
        self.assertFalse(report["release_qualified"])
        self.assertFalse(report["production_node_grpc_worker_qualified"])
        self.assertFalse(report["full_checkout_source_restored"])

    def test_mocked_broker_and_original_test_fail_closed(self):
        inner = {
            "local_clickhouse_relay_qualified": True,
            "owned_kafka_process_stopped": True,
            "owned_kafka_scratch_removed": True,
            "optional_private_kafka_probe": {
                "rust_original_kafka_grpc_ledger_test_pass": False,
                "full_checkout_source_restored": True,
                "blocker": "rust_original_test_deadline_reached",
            },
        }
        with patch.object(w, "kafka_qualify", return_value=inner):
            receipt = w.qualify(self.repo, self.root, self.root, self.root, "/bin/false")
        self.assertFalse(receipt["original_rust_kafka_grpc_test_pass"])
        self.assertEqual(receipt["blocker"], "rust_original_test_deadline_reached")
        self.assertFalse(receipt["release_qualified"])

    def test_even_successful_synthetic_test_never_qualifies_product(self):
        inner = {
            "local_clickhouse_relay_qualified": True,
            "owned_kafka_process_stopped": True,
            "owned_kafka_scratch_removed": True,
            "optional_private_kafka_probe": {
                "rust_original_kafka_grpc_ledger_test_pass": True,
                "full_checkout_source_restored": True,
            },
        }
        with patch.object(w, "kafka_qualify", return_value=inner):
            receipt = w.qualify(self.repo, self.root, self.root, self.root, "/bin/false")
        self.assertTrue(receipt["original_rust_kafka_grpc_test_pass"])
        self.assertFalse(receipt["real_node_ingestion_worker_qualified"])
        self.assertFalse(receipt["durable_clickhouse_qualified"])
        self.assertFalse(receipt["authenticated_tenant_isolation_qualified"])
        self.assertFalse(receipt["release_qualified"])


if __name__ == "__main__":
    unittest.main()
