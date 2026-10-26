"""Wave114: native Rust -> real Kafka -> ClickHouse Kafka Engine, no manual INSERT."""
from __future__ import annotations

import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_capture_clickhouse_wave114 as q
from tools.flind import qualify_native_capture_kafka_wave113 as previous


class CaptureKafkaClickHouseWave114(unittest.TestCase):
    def test_real_native_rust_kafka_clickhouse_uuid_readback(self):
        if (not q.CAPTURE.is_file() or not q.REDIS.is_file()
                or not q.CLICKHOUSE.is_file() or not previous.DEFAULT_HOME.is_dir()):
            self.skipTest("Actual Capture/Redis/Kafka4.3.1/ClickHouse25.12 binaries required")
        result = q.qualify()
        self.assertTrue(result["actual_native_rust_to_kafka_to_clickhouse"], result.get("blocker"))
        self.assertTrue(result["kafka_431_real_broker"])
        self.assertTrue(result["native_capture_delivered_exact_uuid"])
        self.assertTrue(result["clickhouse_kafka_materialized_memory_event"])
        child = result["clickhouse_receipt"]
        self.assertTrue(child["native_kafka_to_real_clickhouse_memory"])
        proof = child["clickhouse_engine_receipt"]
        self.assertTrue(proof["uuid_matches_native_capture_kafka"])
        self.assertTrue(proof["native_rust_record_in_memory_table"])
        self.assertTrue(proof["only_one_native_event"])
        self.assertTrue(proof["separate_synthetic_token_filter"])
        for false_gate in (
            "production_node_ingester_qualified", "production_events_table_qualified",
            "authenticated_tenant_query_qualified", "dashboard_e2e_qualified",
            "release_qualified",
        ):
            with self.subTest(false_gate=false_gate):
                self.assertFalse(result[false_gate])

    def test_malicious_broker_addresses_rejected_before_sql(self):
        good = {
            "uuid": "00000000-0000-0000-0000-000000000001",
            "event": "$pageview", "distinct_id": "flind-wave112-synthetic",
            "token": "flind_synthetic_internal_token",
        }
        for addr in (
            "kafka:9092", "localhost:9092", "8.8.8.8:9092",
            "127.0.0.1:1'; DROP TABLE x", "127.0.0.1:111111",
        ):
            with self.subTest(addr=addr), patch.object(q, "sql") as fake:
                with self.assertRaises(ValueError):
                    q.read_native_kafka_via_clickhouse(8123, addr, good)
                fake.assert_not_called()

    def test_other_or_foreign_kafka_event_rejected_before_sql(self):
        good = {
            "uuid": "00000000-0000-0000-0000-000000000001",
            "event": "$pageview", "distinct_id": "flind-wave112-synthetic",
            "token": "flind_synthetic_internal_token",
        }
        for field, replacement in (
            ("uuid", "not-a-uuid"), ("event", "purchase"),
            ("distinct_id", "foreign-id"), ("token", "foreign-token")
        ):
            with self.subTest(field=field), patch.object(q, "sql") as fake:
                altered = dict(good, **{field: replacement})
                with self.assertRaises(ValueError):
                    q.read_native_kafka_via_clickhouse(8123, "127.0.0.1:19092", altered)
                fake.assert_not_called()

    def test_non_private_or_long_clickhouse_sql_rejected(self):
        with self.assertRaises(ValueError):
            q.sql(0, "SELECT 1")
        with self.assertRaises(ValueError):
            q.sql(8123, "A" * 1501)
        with self.assertRaises(ValueError):
            q.sql(8123, "SELECT '非ASCII'")

    def test_callback_receipt_is_optional_for_previous_native_probe(self):
        params = inspect.signature(previous.real_native_roundtrip).parameters
        self.assertIn("on_native_consumed", params)
        self.assertIsNone(params["on_native_consumed"].default)

    def test_no_manual_insert_and_prod_release_gates_never_promoted(self):
        path = q.Path(__file__).resolve().parents[2] / "tools/flind/qualify_native_capture_clickhouse_wave114.py"
        source = path.read_text()
        self.assertIn("ENGINE=Kafka SETTINGS", source)
        self.assertIn("CREATE MATERIALIZED VIEW", source)
        self.assertIn("ENGINE=Memory", source)
        self.assertNotIn('sql(port, "INSERT ', source)
        for flag in (
            '"production_node_ingester_qualified": False',
            '"production_events_table_qualified": False',
            '"authenticated_tenant_query_qualified": False',
            '"dashboard_e2e_qualified": False',
            '"release_qualified": False',
        ):
            self.assertIn(flag, source)

    def test_missing_binaries_prevent_starting_broker(self):
        with patch.object(q, "CAPTURE", Path("/nonexistent/flind-capture")):
            with patch.object(q, "qualify_kafka") as broker:
                receipt = q.qualify()
                self.assertFalse(receipt["actual_native_rust_to_kafka_to_clickhouse"])
                broker.assert_not_called()
                self.assertFalse(receipt["release_qualified"])


if __name__ == "__main__":
    unittest.main()
