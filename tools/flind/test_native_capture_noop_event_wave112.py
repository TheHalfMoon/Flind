"""Wave112: a genuine native Rust Capture-v1 event ack in NOOP mode.

The server and Redis are real and ephemeral. This deliberately does not claim
persistence to Kafka or ClickHouse.
"""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_capture_server_wave111 as q


class NativeCaptureSyntheticEventWave112(unittest.TestCase):
    def test_real_noop_sink_accepts_synthetic_v1_event_and_cleans_up(self):
        if not q.CAPTURE.is_file() or not q.REDIS.is_file():
            self.skipTest("Native Capture and local Redis binaries required")
        result = q.probe()
        self.assertTrue(result["native_capture_http_bound"], result.get("blocker"))
        self.assertTrue(result["local_redis_started"], result.get("blocker"))
        self.assertTrue(result["real_liveness_http"], result.get("blocker"))
        self.assertEqual(result.get("synthetic_noop_http_status"), 200)
        self.assertTrue(result.get("native_synthetic_noop_acknowledged"))
        self.assertTrue(result.get("synthetic_noop_response_bounded"))
        self.assertTrue(result.get("capture_process_stopped"))
        self.assertTrue(result.get("redis_process_stopped"))
        self.assertFalse(result["real_kafka_delivery"])
        self.assertFalse(result["clickhouse_product_event_readback"])
        self.assertFalse(result["tenant_auth_end_to_end"])
        self.assertFalse(result["release_qualified"])

    def test_synthetic_accepted_uuid_required_for_ok(self):
        # A fixture must never decide "ok" solely from HTTP 200. Require
        # exact UUID acknowledgement (the source uses uuid4 and keyed result).
        source = (q.ROOT / "tools/flind/qualify_native_capture_server_wave111.py").read_text()
        self.assertIn('body.get("results", {}).get(uid, {}).get("result") == "ok"', source)
        self.assertIn('"Authorization": "Bearer flind_synthetic_internal_token"', source)
        self.assertIn('"PostHog-Request-Id": str(uuid4())', source)
        self.assertIn('"PostHog-Sdk-Info": "flind-capture-v1-internal/1.0"', source)

    def test_binary_missing_remains_fail_closed(self):
        with patch.object(q, "CAPTURE", Path("/missing-native-capture-binary")):
            report = q.probe()
        self.assertFalse(report["native_capture_binary_present"])
        self.assertFalse(report["release_qualified"])
        self.assertIn("blocker", report)


if __name__ == "__main__":
    unittest.main()
