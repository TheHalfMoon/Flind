"""Wave118 regression tests: real Rust ingestion-consumer worker health gate."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_ingestion_readiness_wave118 as q


class NativeConsumerReadinessWave118(unittest.TestCase):
    def test_real_native_readiness_worker_fail_closed_then_recovers(self):
        if not q.BINARY.is_file():
            self.skipTest("Native Rust ingestion-consumer binary unavailable")
        report = q.qualify()
        self.assertTrue(report["native_consumer_verified_worker_readiness_qualified"])
        bad = report["no_worker_receipt"]
        good = report["synthetic_healthy_worker_receipt"]
        self.assertTrue(bad["real_native_health_server_bound"])
        self.assertTrue(bad["liveness_always_200"])
        self.assertTrue(bad["unverified_worker_not_ready"])
        self.assertEqual(bad["observed_readiness_codes"], [503])
        # Wave120 adds the Kafka partition assignment guard: synthetic HTTP
        # worker ready alone must never promote native consumer readiness.
        self.assertFalse(good["verified_worker_eventually_ready"])
        self.assertTrue(good["verified_worker_without_kafka_stays_not_ready"])
        self.assertEqual(good["observed_readiness_codes"], [503])
        self.assertTrue(good["liveness_always_200"])
        self.assertGreaterEqual(bad["sample_count"], 3)
        for receipt in (bad, good):
            self.assertTrue(receipt["native_consumer_child_stopped"])
            self.assertTrue(receipt["fake_worker_server_stopped"])
            self.assertFalse(receipt["release_qualified"])
            self.assertFalse(receipt["kafka_connectivity_qualified"])
            self.assertFalse(receipt["real_node_grpc_worker_qualified"])
            self.assertFalse(receipt["real_product_event_ingestion_qualified"])

    def test_missing_executable_blocks_start(self):
        with patch.object(q, "BINARY", Path("/nonexistent-flind-consumer")):
            report = q.probe_worker(False)
        self.assertFalse(report["real_native_health_server_bound"])
        self.assertFalse(report["release_qualified"])
        self.assertIn("blocker", report)

    def test_all_end_to_end_release_claims_stay_false(self):
        with patch.object(q, "BINARY", Path("/nonexistent-flind-consumer")):
            report = q.qualify()
        for name in (
            "real_kafka_connectivity_qualified",
            "node_worker_grpc_pipeline_qualified",
            "durable_product_ingestion_qualified",
            "release_qualified",
        ):
            self.assertFalse(report[name])

    def test_child_environment_is_localhost_only(self):
        path = Path(__file__).resolve().parents[2] / "tools/flind/qualify_native_ingestion_readiness_wave118.py"
        source = path.read_text()
        for literal in (
            '"KAFKA_HOSTS": "127.0.0.1:65441"',
            '"KAFKA_CONSUMER_METADATA_BROKER_LIST": "127.0.0.1:65441"',
            '"WORKER_DISCOVERY_MODE": "static"',
            '"BIND_HOST": "127.0.0.1"',
        ):
            self.assertIn(literal, source)

    def test_worker_fixture_cannot_be_confused_with_real_grpc_worker(self):
        path = Path(__file__).resolve().parents[2] / "tools/flind/qualify_native_ingestion_readiness_wave118.py"
        source = path.read_text()
        self.assertIn("HTTPConnection", source)
        self.assertIn('if self.path != "/_ready"', source)
        self.assertIn('"real_node_grpc_worker_qualified": False', source)


if __name__ == "__main__":
    unittest.main()
