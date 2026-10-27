"""Wave183 original TypeScript converter source attestation and synthetic UUID."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_capture_node_clickhouse_wave183 as w
from tools.flind.qualify_cached_rust_capture_kafka_wave180 import SYNTHETIC_TOKEN, SYNTHETIC_ID

ACK = "00000000-0000-4000-8000-000000000183"


def record() -> dict:
    return {"uuid": ACK, "token": SYNTHETIC_TOKEN, "distinct_id": SYNTHETIC_ID,
            "event": "$pageview", "properties": None}


class NodeConverterWave183(unittest.TestCase):
    def test_original_first_party_converter_is_verified_from_git(self):
        repo = Path("/private/tmp/flind-wave171-current-boot")
        if not repo.exists():
            self.skipTest("Mac scratch source unavailable")
        self.assertTrue(w.verify_source_converter(repo))

    def test_node_original_typescript_converter_preserves_uuid(self):
        result = w.node_adapter(record(), ACK)
        self.assertTrue(result["actual_typescript_deserializer_uuid_verified"])
        self.assertTrue(result["source_record_was_real_native_capture_kafka"])
        self.assertFalse(result["real_node_grpc_worker_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_mismatched_uuid_rejected_before_node(self):
        with patch.object(w, "shutil") as shutil_mock:
            with self.assertRaises(w.Denied):
                w.node_adapter(record(), "00000000-0000-4000-8000-000000000184")
            shutil_mock.which.assert_not_called()

    def test_forged_team_id_refused(self):
        with self.assertRaises(w.Denied):
            w.node_adapter({**record(), "team_id": 202}, ACK)

    def test_non_fixture_event_and_token_refused(self):
        for item in ({"event": "private"}, {"token": "wrong"}, {"distinct_id": "someone"}):
            with self.assertRaises(w.Denied):
                w.node_adapter({**record(), **item}, ACK)

    def test_missing_node_executable_fails_closed(self):
        with patch.object(w.shutil, "which", return_value=None):
            with self.assertRaises(w.Denied):
                w.node_adapter(record(), ACK)

    def test_broker_receipt_does_not_upgrade_worker_auth_or_release(self):
        receipt = {
            "native_capture_http_kafka_clickhouse_uuid_pass": True,
            "actual_typescript_deserializer_uuid_verified": True,
            "owned_kafka_process_stopped": True, "owned_kafka_scratch_removed": True,
            "owned_capture_stopped": True, "owned_redis7_stopped": True,
            "native_event_inserted_rows": 1,
        }
        with patch.object(w, "verify_source_converter", return_value=True), patch.object(
            w, "native_to_clickhouse", return_value=receipt
        ):
            result = w.qualify(Path("/fake"), Path("/fake"), Path("/fake"))
        self.assertTrue(result["native_capture_kafka_node_converter_clickhouse_uuid_pass"])
        for key in (
            "actual_node_ingestion_worker_qualified", "native_rust_kafka_consumer_qualified",
            "durable_clickhouse_ingestion_qualified", "authenticated_tenant_isolation_qualified",
            "sdk_dashboard_browser_e2e_qualified", "release_qualified",
        ):
            self.assertFalse(result[key])

    def test_node_converter_failure_blocks_qualified_chain(self):
        with patch.object(w, "verify_source_converter", return_value=True), patch.object(
            w, "native_to_clickhouse", return_value={
                "native_capture_http_kafka_clickhouse_uuid_pass": True,
                "actual_typescript_deserializer_uuid_verified": False,
                "owned_kafka_process_stopped": True, "owned_kafka_scratch_removed": True,
                "owned_capture_stopped": True, "owned_redis7_stopped": True,
            }
        ):
            result = w.qualify(Path("/fake"), Path("/fake"), Path("/fake"))
        self.assertFalse(result["native_capture_kafka_node_converter_clickhouse_uuid_pass"])
        self.assertFalse(result["release_qualified"])
        self.assertIn("blocker", result)


if __name__ == "__main__":
    unittest.main()
