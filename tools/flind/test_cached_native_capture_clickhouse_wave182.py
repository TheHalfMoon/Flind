"""Wave182 exact native Kafka UUID-to-ClickHouse synthetic-only guardrails."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from tools.flind import qualify_cached_native_capture_clickhouse_wave182 as w
from tools.flind import qualify_cached_rust_capture_kafka_wave180 as native


ACK = "00000000-0000-4000-8000-000000000182"


def fixture() -> dict:
    return {
        "uuid": ACK,
        "token": native.SYNTHETIC_TOKEN,
        "distinct_id": native.SYNTHETIC_ID,
        "event": "$pageview",
        "properties": {"$pathname": "/synthetic", "$geoip_disable": True},
    }


class NativeClickHouse(unittest.TestCase):
    def test_strict_native_ack_uuid_source_projection(self):
        row = w.source_event_row(fixture(), ACK)
        self.assertEqual(row["uuid"], ACK)
        self.assertEqual(row["team_id"], 101)
        self.assertEqual(row["distinct_id"], native.SYNTHETIC_ID)
        self.assertEqual(row["event"], "$pageview")
        self.assertEqual(row["properties"], '{"$pathname":"/synthetic"}')

    def test_rejects_modified_uuid(self):
        changed = {**fixture(), "uuid": "00000000-0000-4000-8000-000000000183"}
        with self.assertRaises(w.NativeRelayRejected):
            w.source_event_row(changed, ACK)

    def test_rejects_client_supplied_team_id(self):
        with self.assertRaises(w.NativeRelayRejected):
            w.source_event_row({**fixture(), "team_id": 202}, ACK)

    def test_rejects_mismatched_or_nonfixture_token(self):
        for token in ("", "flind_other_client_token", None, "flind_wave180_prod"):
            with self.assertRaises(w.NativeRelayRejected):
                w.source_event_row({**fixture(), "token": token}, ACK)

    def test_rejects_payload_and_path_mutations(self):
        for changes in (
            {"distinct_id": "different-person"}, {"event": "other_event"},
            {"properties": {"$pathname": "/private"}},
            {"properties": ["not", "a", "dict"]},
        ):
            with self.assertRaises(w.NativeRelayRejected):
                w.source_event_row({**fixture(), **changes}, ACK)

    def test_properties_may_be_valid_json_text(self):
        event = {**fixture(), "properties": '{"$pathname":"/synthetic"}'}
        row = w.source_event_row(event, ACK)
        self.assertEqual(row["team_id"], 101)

    def test_native_capture_may_remove_optional_pathname(self):
        row = w.source_event_row({**fixture(), "properties": {"other": "synthetic"}}, ACK)
        self.assertEqual(row["properties"], "{}")  # Never forge the missing path.
        self.assertEqual(row["uuid"], ACK)
        self.assertEqual(row["team_id"], 101)

    def test_native_kafka_envelope_with_null_properties_is_valid(self):
        row = w.source_event_row({**fixture(), "properties": None}, ACK)
        self.assertEqual(row["properties"], "{}")
        self.assertEqual(row["uuid"], ACK)
        self.assertEqual(row["team_id"], 101)

    def test_invalid_or_oversized_properties_refused(self):
        for props in ("{", "x" * 17000, {"$pathname": "/synthetic", "big": "x" * 17000}):
            with self.assertRaises(w.NativeRelayRejected):
                w.source_event_row({**fixture(), "properties": props}, ACK)

    def test_invalid_acknowledged_uuid_refused(self):
        with self.assertRaises(w.NativeRelayRejected):
            w.source_event_row(fixture(), "unverified-uuid")

    def test_unsupported_clickhouse_refused_before_kafka(self):
        with patch.object(w, "checked_scratch"), patch.object(
            w, "source_clickhouse_spec", return_value=("a" * 40, ">=24.8,<=25.12")
        ), patch.object(
            w, "binary_clickhouse_version", return_value="26.10.2.103"
        ), patch.object(w, "isolated_kafka") as kafka:
            receipt = w.qualify(Path("/fake"), Path("/fake"), Path("/fake"))
        kafka.assert_not_called()
        self.assertFalse(receipt["native_capture_http_kafka_clickhouse_uuid_pass"])
        self.assertFalse(receipt["release_qualified"])

    def test_forged_native_downstream_cannot_promote_release(self):
        base = {
            "local_clickhouse_relay_qualified": True,
            "owned_kafka_process_stopped": True,
            "owned_kafka_scratch_removed": True,
            "optional_private_kafka_probe": {
                "real_cached_rust_capture_http_qualified": True,
                "native_kafka_uuid_readback_qualified": True,
                "owned_capture_stopped": True,
                "owned_redis7_stopped": True,
                "optional_native_downstream": {
                    "native_capture_ack_uuid_stored_in_clickhouse": True,
                    "native_clickhouse_uuid_exact_match": True,
                    "native_event_inserted_rows": 1,
                }
            }
        }
        with patch.object(w, "checked_scratch"), patch.object(
            w, "source_clickhouse_spec", return_value=("b" * 40, ">=24.8,<=25.12")
        ), patch.object(
            w, "binary_clickhouse_version", return_value="25.12.7.21"
        ), patch.object(w, "checked_capture", return_value=True), patch.object(
            w, "isolated_kafka", return_value=base
        ):
            receipt = w.qualify(Path("/fake"), Path("/fake"), Path("/fake"))
        self.assertTrue(receipt["native_capture_http_kafka_clickhouse_uuid_pass"])
        for flag in (
            "native_rust_consumer_qualified", "node_grpc_worker_qualified",
            "durable_clickhouse_ingestion_qualified", "flind_sdk_dashboard_e2e_qualified",
            "authenticated_tenant_isolation_qualified", "release_qualified",
        ):
            self.assertFalse(receipt[flag])


if __name__ == "__main__":
    unittest.main()
