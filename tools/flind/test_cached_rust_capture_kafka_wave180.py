"""Wave180 cached Rust Capture to private Kafka qualification guards."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_cached_rust_capture_kafka_wave180 as w


class CaptureKafkaGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="flind-wave180-", dir="/private/tmp")
        self.root = Path(self.temp.name)
        self.scratch = self.root / "owned"
        self.scratch.mkdir()
        (self.scratch / ".flind-wave179-owned").write_text("FLIND_WAVE179_SCRATCH_V1\n")
        self.fake_redis = self.root / "redis"
        self.fake_redis.write_bytes(b"synthetic executable marker")
        self.fake_redis.chmod(0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_private_loopback_and_marked_broker_required(self):
        with patch.object(w, "REDIS7", self.fake_redis), patch.object(w, "checked_capture", return_value=True):
            self.assertTrue(w.admitted_native("127.0.0.1:19092", self.scratch))
            for broker in ("localhost:19092", "0.0.0.0:19092", "broker.example.com:19092", "", "127.0.0.1:bad"):
                self.assertFalse(w.admitted_native(broker, self.scratch))

    def test_missing_marker_refused_before_network(self):
        (self.scratch / ".flind-wave179-owned").unlink()
        with patch.object(w, "REDIS7", self.fake_redis), patch.object(w, "checked_capture", return_value=True):
            self.assertFalse(w.admitted_native("127.0.0.1:19092", self.scratch))

    def test_wrong_marker_refused(self):
        (self.scratch / ".flind-wave179-owned").write_text("WRONG\n")
        with patch.object(w, "REDIS7", self.fake_redis), patch.object(w, "checked_capture", return_value=True):
            self.assertFalse(w.admitted_native("127.0.0.1:19092", self.scratch))

    def test_wrong_binary_digest_blocks_native_probe(self):
        with patch.object(w, "REDIS7", self.fake_redis), patch.object(w, "checked_capture", return_value=False):
            self.assertFalse(w.admitted_native("127.0.0.1:19092", self.scratch))

    def test_unapproved_synthetic_recipient_not_changed(self):
        self.assertEqual(w.TOPIC, "flind_wave180_first_party_native_capture")
        self.assertEqual(w.GROUP, "flind-wave180-native-synthetic")
        self.assertEqual(w.SYNTHETIC_TOKEN, "flind_synthetic_internal_token")
        self.assertEqual(w.SYNTHETIC_ID, "flind-wave112-synthetic")

    def test_scoped_http_path_and_binary_digest_are_fixed(self):
        self.assertEqual(w.PROBE_PATH, "/i/v1/analytics/events")
        self.assertEqual(len(w.EXPECTED_CAPTURE_SHA256), 64)
        self.assertNotEqual(w.EXPECTED_CAPTURE_SHA256, "0"*64)

    def test_native_probe_denies_unsafe_target_without_opening_service(self):
        r = w.private_capture_probe("0.0.0.0:19092", self.scratch)
        self.assertFalse(r["real_cached_rust_capture_http_qualified"])
        self.assertFalse(r["first_party_ingestion_worker_qualified"])
        self.assertFalse(r["release_qualified"])
        self.assertTrue(r["owned_redis7_stopped"])
        self.assertTrue(r["owned_capture_stopped"])

    def test_spoofed_broker_result_does_not_qualify_product(self):
        receipt = {
            "local_clickhouse_relay_qualified": True,
            "kafka_431_broker_qualified": True,
            "owned_kafka_process_stopped": True,
            "owned_kafka_scratch_removed": True,
            "source_commit": "a"*40,
            "optional_private_kafka_probe": {
                "real_cached_rust_capture_http_qualified": False,
                "native_kafka_uuid_readback_qualified": False,
            }
        }
        with patch.object(w, "qualify_kafka_relay", return_value=receipt):
            result = w.qualify(self.root, self.root, self.root)
        self.assertFalse(result["cached_rust_capture_to_real_kafka_qualified"])
        self.assertFalse(result["authenticated_tenant_isolation_qualified"])
        self.assertFalse(result["release_qualified"])
        self.assertIn("blocker", result)


if __name__ == "__main__":
    unittest.main()
