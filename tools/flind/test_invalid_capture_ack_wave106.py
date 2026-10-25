"""Wave106 regression checks: malformed HTTP ack receipts stay fail-closed."""
from __future__ import annotations

import http.client
from http.server import ThreadingHTTPServer
import json
from threading import Thread
import unittest
from unittest.mock import patch

from tools.flind import qualify_invalid_capture_ack_wave106 as q


class CaptureMalformedAckWave106(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), q.FakeMalformedCaptureV1)
        self.server.daemon_threads = True
        self.server.receipts = []
        self.worker = Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=4)

    def post(self, uid: str, path=q.ENDPOINT, *, raw=None):
        if raw is None:
            raw = json.dumps({
                "capture_internal": True,
                "batch": [{"uuid": uid}],
            }).encode()
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        client.request("POST", path, body=raw, headers={
            "Authorization": "Bearer synthetic_token",
            "User-Agent": "flind-capture-v1-internal/1.0",
            "PostHog-Sdk-Info": "flind-capture-v1-internal/1.0",
            "Content-Type": "application/json",
        })
        resp = client.getresponse()
        status, body = resp.status, resp.read()
        client.close()
        return status, body

    def test_first_response_is_http_200_but_no_event_status(self):
        uid = list(q.CASES)[0]
        status, raw = self.post(uid)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), {"results": {uid: {}}})
        self.assertEqual(self.server.receipts[0]["uuid"], uid)

    def test_unhashable_status_is_returned_to_real_producer(self):
        uid = list(q.CASES)[1]
        status, raw = self.post(uid)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["results"][uid]["result"], ["ok"])

    def test_nonobject_failure_body_is_http_422(self):
        status, raw = self.post(list(q.CASES)[2])
        self.assertEqual(status, 422)
        self.assertIsInstance(json.loads(raw), list)

    def test_valid_ack_preserved(self):
        uid = list(q.CASES)[3]
        status, raw = self.post(uid)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["results"][uid]["result"], "ok")

    def test_unknown_event_id_rejected_before_receipt(self):
        status, _ = self.post("unknown")
        self.assertEqual(status, 400)
        self.assertEqual(self.server.receipts, [])

    def test_wrong_capture_path_rejected(self):
        status, _ = self.post(list(q.CASES)[0], path="/wrong")
        self.assertEqual(status, 404)
        self.assertEqual(self.server.receipts, [])

    def test_oversized_body_rejected(self):
        status, _ = self.post(list(q.CASES)[0], raw=b"x" * 8001)
        self.assertEqual(status, 400)

    def test_missing_lock_refuses_capture(self):
        with patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": False}):
            result = q.qualify_invalid_ack_http()
        self.assertFalse(result["real_capture_invalid_ack_http_qualified"])

    def test_cannot_promote_fake_receiver_into_release(self):
        result = q.refused("synthetic")
        for key in (
            "production_capture_rust_qualified",
            "production_kafka_ingestion_qualified",
            "product_clickhouse_schema_qualified",
            "product_query_api_qualified",
            "dashboard_e2e_qualified",
            "release_qualified",
        ):
            self.assertFalse(result[key])


if __name__ == "__main__":
    unittest.main()
