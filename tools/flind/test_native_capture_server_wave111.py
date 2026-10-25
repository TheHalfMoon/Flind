"""Wave111 tests: ACTUAL native Capture executable over loopback and cleanup."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_capture_server_wave111 as q


class NativeCaptureRuntimeWave111(unittest.TestCase):
    def test_real_native_executable_boots_and_refuses_unauthorized_capture(self):
        if not q.CAPTURE.is_file() or not q.REDIS.is_file():
            self.skipTest("Native Capture/Redis must be prebuilt locally")
        proof = q.probe()
        for field in (
            "native_capture_binary_present", "local_redis_started",
            "native_capture_http_bound", "real_liveness_http",
            "invalid_capture_headers_rejected", "no_kafka_sink_enabled",
            "loopback_only", "capture_process_stopped", "redis_process_stopped",
        ):
            with self.subTest(field=field):
                self.assertTrue(proof.get(field), proof.get("blocker", ""))
        self.assertEqual(proof["liveness_http_status"], 200)
        self.assertEqual(proof["invalid_capture_http_status"], 401)
        self.assertFalse(proof["real_kafka_delivery"])
        self.assertFalse(proof["clickhouse_product_event_readback"])
        self.assertFalse(proof["tenant_auth_end_to_end"])
        self.assertFalse(proof["release_qualified"])

    def test_missing_binary_fails_without_starting_services(self):
        with patch.object(q, "CAPTURE", Path("/not-installed-flind-capture-binary")):
            receipt = q.probe()
        self.assertFalse(receipt["native_capture_binary_present"])
        self.assertIn("blocker", receipt)
        self.assertFalse(receipt["native_capture_http_bound"])

    def test_missing_redis_binary_fails_closed(self):
        with patch.object(q, "REDIS", Path("/not-installed-flind-redis-binary")):
            receipt = q.probe()
        self.assertIn("blocker", receipt)
        self.assertFalse(receipt["local_redis_started"])

    def test_capture_cleanup_kills_child_subprocess(self):
        p = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(15)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            q.terminate(p)
            self.assertIsNotNone(p.poll())
        finally:
            q.terminate(p)

    def test_ephemeral_capture_uses_no_sink_and_loopback_only(self):
        source = (q.ROOT / "tools/flind/qualify_native_capture_server_wave111.py").read_text()
        for required in (
            '"NOOP_SINK": "true"', '"PRINT_SINK": "false"',
            '"KAFKA_HOSTS": "127.0.0.1:65441"',
            '"ADDRESS": f"127.0.0.1:{capture_port}"',
            '"--bind", "127.0.0.1"', '"--appendonly", "no"',
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
