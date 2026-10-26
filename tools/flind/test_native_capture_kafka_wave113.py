"""Wave113: live Rust Capture -> Kafka 4.3.1 -> native consumer UUID proof."""
from __future__ import annotations

import inspect
from pathlib import Path
import unittest

from tools.flind import qualify_native_capture_kafka_wave113 as q
from tools.flind import qualify_ephemeral_kafka_wave84 as k


class NativeRustToKafkaWave113(unittest.TestCase):
    def test_live_private_kafka_broker_receives_exact_native_rust_event(self):
        if not q.CAPTURE.is_file() or not q.REDIS.is_file() or not q.DEFAULT_HOME.is_dir():
            self.skipTest("Prebuilt native Rust Capture, Redis and Kafka required")
        result = q.qualify(q.DEFAULT_HOME)
        self.assertTrue(result["actual_native_rust_capture_to_real_kafka"], result.get("blocker"))
        self.assertTrue(result["isolated_kafka_431_passed"])
        child = result["native_capture_receipt"]
        for field in (
            "actual_native_capture_kafka_roundtrip",
            "native_rust_http_bound",
            "native_event_ack_ok",
            "native_event_uuid_read_back_from_kafka",
            "private_kafka_431_broker", "real_redis_local",
            "no_noop_sink", "owned_capture_stopped", "owned_redis_stopped",
        ):
            with self.subTest(field=field):
                self.assertTrue(child[field])
        self.assertEqual(child["native_http_status"], 200)
        self.assertFalse(child["production_clickhouse_ingestion"])
        self.assertFalse(child["production_query_api"])
        self.assertFalse(result["tenant_auth_end_to_end"])
        self.assertFalse(result["release_qualified"])

    def test_missing_kafka_distribution_refused(self):
        result = q.qualify(Path("/nonexistent-flind-kafka-home"))
        self.assertFalse(result.get("actual_native_rust_capture_to_real_kafka", False))
        self.assertFalse(result["release_qualified"])

    def test_fixture_does_not_promote_any_product_release_gate(self):
        receipt = q.refused("unavailable")
        for flag in ("actual_native_capture_kafka_roundtrip",
                     "native_event_uuid_read_back_from_kafka",
                     "production_clickhouse_ingestion", "production_query_api",
                     "tenant_auth_end_to_end", "dashboard_browser_e2e",
                     "release_qualified"):
            self.assertFalse(receipt[flag])

    def test_existing_kafka_api_is_backward_compatible(self):
        params = inspect.signature(k.qualify_kafka).parameters
        self.assertIn("on_consumed", params)
        self.assertIn("on_broker_ready", params)
        self.assertIsNone(params["on_broker_ready"].default)

    def test_native_kafka_mode_is_real_producer_not_noop(self):
        source = (q.Path(__file__).resolve().parents[2] /
                  "tools/flind/qualify_native_capture_kafka_wave113.py").read_text()
        for expected in (
            '"NOOP_SINK": "false"', '"KAFKA_INGESTION_PRODUCER_METADATA_BROKER_LIST"',
            '"native_event_uuid_read_back_from_kafka"',
            '"--from-beginning", "--max-messages", "1"',
            '"--bind", "127.0.0.1"',
        ):
            self.assertIn(expected, source)


if __name__ == "__main__":
    unittest.main()
