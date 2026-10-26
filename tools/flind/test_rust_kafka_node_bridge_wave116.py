"""Wave116 focused real Kafka-to-production-Node-adapter integration guards."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from tools.flind import qualify_rust_kafka_node_bridge_wave116 as q


class KafkaNodeBridgeWave116(unittest.TestCase):
    GOOD = {
        "uuid": "00000000-0000-0000-0000-000000000016",
        "event": "$pageview",
        "distinct_id": "flind-wave112-synthetic",
        "token": "flind_synthetic_internal_token",
    }

    def test_actual_native_rust_kafka_node_function_roundtrip(self):
        if not q.CAPTURE.is_file() or not q.REDIS.is_file() or not q.DEFAULT_HOME.is_dir():
            self.skipTest("Native Rust Capture/Redis/Kafka 4.3.1 required")
        actual = q.qualify()
        self.assertTrue(actual["real_rust_capture_to_kafka_to_node_adapter"], actual.get("blocker"))
        self.assertTrue(actual["real_kafka_431_broker"])
        self.assertTrue(actual["native_rust_to_kafka_uuid_verified"])
        child = actual["node_adapter_receipt"]
        self.assertTrue(child["native_kafka_event_node_adapter_passed"])
        self.assertTrue(child["uuid_preserved_in_node_buffer"])
        self.assertTrue(child["production_typescript_deserializer_executed"])
        for forbidden in (
            "production_node_ingestion_worker_qualified",
            "real_rust_grpc_consumer_api_qualified",
            "real_production_clickhouse_ingestion_qualified",
            "tenant_query_api_qualified",
            "browser_dashboard_e2e_qualified",
            "release_qualified",
        ):
            self.assertFalse(actual[forbidden], forbidden)

    def test_direct_production_node_function_receipt(self):
        actual = q.node_adapter_receipt("127.0.0.1:19092", self.GOOD)
        self.assertTrue(actual["native_kafka_event_node_adapter_passed"], actual.get("blocker"))
        self.assertTrue(actual["uuid_preserved_in_node_buffer"])
        self.assertFalse(actual["production_ingestion_worker_started"])
        self.assertFalse(actual["release_qualified"])

    def test_foreign_event_fails_before_node_subprocess(self):
        for field, replacement in (
            ("event", "purchase"),
            ("distinct_id", "external-user"),
            ("token", "external-token"),
        ):
            with self.subTest(field=field), patch.object(q.subprocess, "run") as run:
                actual = q.node_adapter_receipt(
                    "127.0.0.1:19092",
                    {**self.GOOD, field: replacement},
                )
                self.assertFalse(actual["native_kafka_event_node_adapter_passed"])
                run.assert_not_called()

    def test_nonlocal_broker_fails_before_node(self):
        with patch.object(q.subprocess, "run") as run:
            actual = q.node_adapter_receipt("external.kafka.invalid:9092", self.GOOD)
            self.assertFalse(actual["native_kafka_event_node_adapter_passed"])
            run.assert_not_called()

    def test_oversized_native_event_fails_before_node(self):
        with patch.object(q.subprocess, "run") as run:
            actual = q.node_adapter_receipt(
                "127.0.0.1:19092",
                {**self.GOOD, "oversized": "x" * 35000},
            )
            self.assertFalse(actual["native_kafka_event_node_adapter_passed"])
            run.assert_not_called()

    def test_bad_uuid_refused_in_node_fixture(self):
        payload = {
            "topic": q.TOPIC,
            "event": {**self.GOOD, "uuid": "bad-uuid"},
        }
        result = subprocess.run(
            ["node", "--no-warnings", "--experimental-strip-types", str(q.NODE_SCRIPT)],
            input=json.dumps(payload), text=True, capture_output=True, cwd=q.ROOT, timeout=8,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout)

    def test_wrong_kafka_topic_refused_by_node(self):
        payload = {"topic": "other_topic", "event": self.GOOD}
        result = subprocess.run(
            ["node", "--no-warnings", "--experimental-strip-types", str(q.NODE_SCRIPT)],
            input=json.dumps(payload), text=True, capture_output=True, cwd=q.ROOT, timeout=8,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout)

    def test_missing_capture_binary_does_not_launch_services(self):
        with patch.object(q, "CAPTURE", Path("/not-a-real-flind-capture")):
            with patch.object(q, "qualify_kafka") as kafka:
                actual = q.qualify()
                self.assertFalse(actual["real_rust_capture_to_kafka_to_node_adapter"])
                kafka.assert_not_called()

    def test_receipt_never_promotes_full_worker(self):
        actual = q.node_adapter_receipt("127.0.0.1:19092", self.GOOD)
        self.assertFalse(actual["production_ingestion_worker_started"])
        self.assertFalse(actual["real_rust_grpc_consumer_qualified"])
        self.assertFalse(actual["product_clickhouse_event_schema_qualified"])
        self.assertFalse(actual["authenticated_query_api_qualified"])
        self.assertFalse(actual["release_qualified"])


if __name__ == "__main__":
    unittest.main()
