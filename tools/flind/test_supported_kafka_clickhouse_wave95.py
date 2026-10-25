"""Wave95: real supported Kafka/ClickHouse relay must never claim production."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_supported_kafka_clickhouse_wave95 as q


class SupportedKafkaClickhouseWave95(unittest.TestCase):
    HOME = Path("/synthetic/kafka")
    BIN = "/synthetic/clickhouse"

    def _mock_admission(self):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(q, "source_requirements", return_value={"clickhouse": ">=24.8,<=25.12"}))
        stack.enter_context(patch.object(q, "inspect_binary", return_value={
            "supported_version": True, "observed_version": "25.12.7.21"
        }))
        return stack

    def test_missing_binary_rejected_before_kafka_launch(self):
        with patch.object(q, "qualify_kafka") as kafka:
            receipt = q.qualify_supported_relay(self.HOME, "/no/flind/clickhouse")
        self.assertFalse(receipt["supported_kafka_clickhouse_synthetic_relay_qualified"])
        self.assertFalse(receipt["release_qualified"])
        kafka.assert_not_called()

    def test_unknown_source_version_spec_fails_closed(self):
        with patch.object(q, "source_requirements", side_effect=ValueError("spec missing")), patch.object(q, "qualify_kafka") as kafka:
            receipt = q.qualify_supported_relay(self.HOME, self.BIN)
        self.assertFalse(receipt["supported_kafka_clickhouse_synthetic_relay_qualified"])
        kafka.assert_not_called()

    def test_valid_versions_and_real_flow_receipt(self):
        with self._mock_admission(), patch.object(q, "sql_http", return_value=b"25.12.7.21"), patch.object(q, "relay_readback", return_value={
            "synthetic_relay_passed": True,
            "cross_team_path_reads_absent": True,
            "kafka_records_replayed": 3,
        }) as readback:
            def clickhouse(*, binary, on_ready):
                self.assertEqual(binary, self.BIN)
                return {"isolated_clickhouse_passed": True, "event_readback": on_ready(18123)}
            def kafka(home, *, on_consumed):
                self.assertEqual(home, self.HOME)
                return {
                    "isolated_kafka_passed": True,
                    "exact_json_message_roundtrip": True,
                    "synthetic_events_consumed": 3,
                    "synthetic_relay": on_consumed(q.EVENTS),
                }
            with patch.object(q, "isolated_clickhouse", side_effect=clickhouse), patch.object(q, "qualify_kafka", side_effect=kafka):
                receipt = q.qualify_supported_relay(self.HOME, self.BIN)
        self.assertTrue(receipt["supported_kafka_clickhouse_synthetic_relay_qualified"])
        self.assertTrue(receipt["supported_clickhouse_runtime_passed"])
        readback.assert_called_once_with(18123, q.EVENTS)
        self.assertEqual(receipt["synthetic_event_count"], 3)
        for name in (
            "production_sdk_ingestion_qualified",
            "production_kafka_consumer_qualified",
            "production_clickhouse_schema_qualified",
            "dashboard_query_qualified",
            "tenant_authorization_qualified",
            "release_qualified",
        ):
            self.assertIs(receipt[name], False)

    def test_incompatible_actual_running_version_is_refused(self):
        with self._mock_admission(), patch.object(q, "sql_http", return_value=b"26.10.2.103"), patch.object(q, "relay_readback") as readback:
            def clickhouse(*, binary, on_ready):
                try:
                    on_ready(18123)
                except ValueError:
                    return {"isolated_clickhouse_passed": False}
                self.fail("Invalid runtime version was accepted")
            def kafka(home, *, on_consumed):
                return {"isolated_kafka_passed": True, "exact_json_message_roundtrip": True,
                        "synthetic_events_consumed": 3, "synthetic_relay": on_consumed(q.EVENTS)}
            with patch.object(q, "isolated_clickhouse", side_effect=clickhouse), patch.object(q, "qualify_kafka", side_effect=kafka):
                result = q.qualify_supported_relay(self.HOME, self.BIN)
        self.assertFalse(result["supported_kafka_clickhouse_synthetic_relay_qualified"])
        readback.assert_not_called()

    def test_mismatched_kafka_records_are_never_replayed(self):
        with self._mock_admission(), patch.object(q, "isolated_clickhouse") as clickhouse:
            def kafka(home, *, on_consumed):
                wrong = ({**q.EVENTS[0], "team_id": 909},) + q.EVENTS[1:]
                with self.assertRaises(ValueError):
                    on_consumed(wrong)
                return {"isolated_kafka_passed": False}
            with patch.object(q, "qualify_kafka", side_effect=kafka):
                receipt = q.qualify_supported_relay(self.HOME, self.BIN)
        self.assertFalse(receipt["supported_kafka_clickhouse_synthetic_relay_qualified"])
        clickhouse.assert_not_called()

    def test_inconsistent_component_receipt_is_not_promoted(self):
        with self._mock_admission():
            fake = {"isolated_kafka_passed": False, "exact_json_message_roundtrip": True,
                    "synthetic_events_consumed": 3,
                    "synthetic_relay": {"supported_clickhouse_relay_passed": True,
                                        "running_version_supported": True, "readback_rows": 3}}
            with patch.object(q, "qualify_kafka", return_value=fake):
                report = q.qualify_supported_relay(self.HOME, self.BIN)
        self.assertFalse(report["supported_kafka_clickhouse_synthetic_relay_qualified"])

    def test_actual_script_declares_no_release_claim(self):
        code = Path(q.__file__).read_text(encoding="utf-8")
        self.assertIn('"release_qualified": False', code)
        self.assertIn('"production_sdk_ingestion_qualified": False', code)
        self.assertIn('sql_http(port, "SELECT version()")', code)
        self.assertIn('version_matches_spec(observed, spec)', code)


if __name__ == "__main__":
    unittest.main()
