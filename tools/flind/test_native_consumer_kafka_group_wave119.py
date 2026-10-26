"""Wave119 — real native Rust ingestion consumer joins private Kafka group."""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_consumer_kafka_group_wave119 as q


class NativeConsumerKafkaWave119(unittest.TestCase):
    def test_actual_native_rust_consumer_group_membership(self):
        if not q.CONSUMER.is_file() or not q.DEFAULT_HOME.is_dir():
            self.skipTest("Native ingestion-consumer and private Kafka 4.3.1 required")
        report = q.qualify()
        self.assertTrue(report["isolated_kafka_431_passed"])
        self.assertTrue(report["actual_native_rust_consumer_kafka_group_qualified"], report.get("blocker"))
        child = report["native_receipt"]
        for label in (
            "real_native_consumer_executable",
            "real_kafka_431_group_join",
            "real_native_health_bound",
            "native_readiness_worker_gate",
            "owned_native_consumer_stopped",
            "owned_fake_worker_stopped",
        ):
            with self.subTest(label=label):
                self.assertTrue(child[label])
        self.assertIn(200, child["readiness_codes_observed"])
        for label in (
            "node_grpc_worker_qualified", "kafka_event_processing_qualified",
            "kafka_ack_offset_commit_qualified", "clickhouse_product_schema_qualified",
            "release_qualified",
        ):
            with self.subTest(label=label):
                self.assertFalse(report[label])

    def test_missing_consumer_fails_closed(self):
        with patch.object(q, "CONSUMER", Path("/nonexistent-native-consumer")):
            result = q.within_broker("127.0.0.1:39092")
        self.assertFalse(result["real_kafka_431_group_join"])
        self.assertFalse(result["release_qualified"])

    def test_nonlocal_kafka_is_rejected(self):
        with patch.object(q, "qualify_kafka") as mocked:
            # Broker should not be consulted when direct native callback receives
            # a non-loopback host; no external connections.
            result = q.within_broker("kafka.example.com:9092")
        mocked.assert_not_called()
        self.assertFalse(result["real_kafka_431_group_join"])
        self.assertIn("blocker", result)

    def test_sanitized_child_configuration_and_group_verification(self):
        text = (q.Path(__file__).resolve().parents[2] /
                "tools/flind/qualify_native_consumer_kafka_group_wave119.py").read_text()
        for expected in (
            '"KAFKA_CONSUMER_AUTO_OFFSET_RESET": "earliest"',
            '"KAFKA_CONSUMER_GROUP_ID": GROUP',
            '"INGESTION_CONSUMER_GROUP_ID": GROUP',
            '"WORKER_DISCOVERY_MODE": "static"',
            '"BIND_HOST": "127.0.0.1"',
            '"--describe", "--group", GROUP, "--state"',
            'and "Stable" in cols',
            'and cols[-1] == "1"',
        ):
            self.assertIn(expected, text)

    def test_no_qualification_of_batch_processing(self):
        text = (q.Path(__file__).resolve().parents[2] /
                "tools/flind/qualify_native_consumer_kafka_group_wave119.py").read_text()
        for expected in (
            '"events_processed_with_real_worker": False',
            '"kafka_offsets_committed_after_ack": False',
            '"production_clickhouse_schema_qualified": False',
            '"release_qualified": False',
        ):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
