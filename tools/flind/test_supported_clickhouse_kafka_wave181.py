"""Wave181: exact first-party ClickHouse version admission and release guard tests."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.qualify_supported_clickhouse_kafka_wave181 import (
    Unsupported, binary_clickhouse_version, qualify,
    source_clickhouse_spec, version_qualified,
)


class SupportedKafkaClickHouse(unittest.TestCase):
    def test_supported_first_party_clickhouse_version_ranges(self):
        spec = ">=24.8,<=25.12"
        for version in ("24.8.0.1", "24.12.9.1", "25.12.7.21", "25.1.4.0"):
            self.assertTrue(version_qualified(version, spec))
        for version in ("24.7.9.1", "23.11.0", "26.10.2.103", "26.0.0"):
            self.assertFalse(version_qualified(version, spec))

    def test_malformed_or_untrusted_requirements_fail_closed(self):
        for clause in ("", "latest", "25.12", ">=24.8; rm -rf /", "<=25.12,>26.0",
                       ">=24.8,<=25.12,rm"):
            self.assertFalse(version_qualified("25.12.7.21", clause))
        for version in ("", "25.12", "v25.12.7", "25.12.7; malicious"):
            self.assertFalse(version_qualified(version, ">=24.8,<=25.12"))

    def test_invalid_clickhouse_binary_path_fails_before_broker(self):
        with self.assertRaises(Unsupported):
            binary_clickhouse_version(Path("/private/tmp/flind-no-clickhouse-binary"))

    def test_source_version_mismatch_never_launches_kafka(self):
        with patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.source_clickhouse_spec",
            return_value=("0"*40, ">=24.8,<=25.12"),
        ), patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.binary_clickhouse_version",
            return_value="26.10.2.103",
        ), patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.real_kafka_relay"
        ) as broker:
            report = qualify(Path("/fake"), Path("/fake"), Path("/fake"), Path("/fake"))
        self.assertEqual(report["blocker"], "clickhouse_binary_outside_first_party_source_range")
        self.assertFalse(report["clickhouse_source_version_supported"])
        self.assertFalse(report["release_qualified"])
        broker.assert_not_called()

    def test_unqualified_inner_broker_cannot_promote_success(self):
        with patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.source_clickhouse_spec",
            return_value=("a"*40, ">=24.8,<=25.12"),
        ), patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.binary_clickhouse_version",
            return_value="25.12.7.21",
        ), patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.real_kafka_relay",
            return_value={
                "local_clickhouse_relay_qualified": True,
                "kafka_431_broker_qualified": False,
                "real_kafka_producer_ack_qualified": True,
                "real_kafka_consumer_qualified": True,
                "owned_kafka_process_stopped": True,
                "owned_kafka_scratch_removed": True,
            },
        ):
            report = qualify(Path("/fake"), Path("/fake"), Path("/fake"), Path("/fake"))
        self.assertFalse(report["real_kafka_to_supported_clickhouse_synthetic_relay_qualified"])
        self.assertFalse(report["release_qualified"])
        self.assertIn("blocker", report)

    def test_supported_source_and_actual_kafka_success_still_not_product_e2e(self):
        with patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.source_clickhouse_spec",
            return_value=("b"*40, ">=24.8,<=25.12"),
        ), patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.binary_clickhouse_version",
            return_value="25.12.7.21",
        ), patch(
            "tools.flind.qualify_supported_clickhouse_kafka_wave181.real_kafka_relay",
            return_value={
                "local_clickhouse_relay_qualified": True,
                "kafka_431_broker_qualified": True,
                "real_kafka_producer_ack_qualified": True,
                "real_kafka_consumer_qualified": True,
                "owned_kafka_process_stopped": True,
                "owned_kafka_scratch_removed": True,
                "synthetic_kafka_event_count": 3,
                "synthetic_rows_inserted": 3,
            },
        ):
            report = qualify(Path("/fake"), Path("/fake"), Path("/fake"), Path("/fake"))
        self.assertTrue(report["real_kafka_to_supported_clickhouse_synthetic_relay_qualified"])
        for key in (
            "production_clickhouse_kafka_ingestion_qualified",
            "first_party_rust_to_clickhouse_ingestion_qualified",
            "authenticated_tenant_isolation_qualified", "flind_sdk_dashboard_e2e_qualified",
            "release_qualified",
        ):
            self.assertFalse(report[key])

    def test_does_not_infer_clickhouse_26_from_cli_success(self):
        self.assertFalse(version_qualified("26.10.2.103", ">=24.8,<=25.12"))

    def test_rejects_version_semantic_downgrade(self):
        self.assertFalse(version_qualified("24.7.20.0", ">=24.8,<=25.12"))
        self.assertFalse(version_qualified("25.13.0", ">=24.8,<=25.12"))


if __name__ == "__main__":
    unittest.main()
