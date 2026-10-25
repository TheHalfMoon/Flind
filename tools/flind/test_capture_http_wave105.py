"""Wave105 bounded real loopback HTTP fixture and release-gate tests."""
import http.client
import json
from threading import Thread
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from tools.flind import qualify_capture_http_wave105 as q


class CaptureHttpWave105(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), q.CaptureStub)
        self.server.requests = []
        self.worker = Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=4)

    def post(self, *, url=q.ENDPOINT, ids=None, raw=None):
        if ids is None:
            ids = list(q.FIXED_IDS[:2])
        if raw is None:
            raw = json.dumps({
                "created_at": "2026-10-26T00:00:00+00:00",
                "capture_internal": True,
                "historical_migration": False,
                "batch": [{
                    "uuid": uid, "event": "$pageview", "distinct_id": "synthetic",
                    "timestamp": "2026-10-26T00:00:00+00:00", "properties": {}
                } for uid in ids],
            }).encode()
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        conn.request("POST", url, body=raw, headers={
            "Authorization": "Bearer synthetic_local",
            "User-Agent": "flind-capture-v1-internal/1.0",
            "PostHog-Sdk-Info": "flind-capture-v1-internal/1.0",
            "PostHog-Attempt": "1",
            "Content-Type": "application/json",
        })
        response = conn.getresponse()
        status, body = response.status, response.read()
        conn.close()
        return status, body

    def test_fixture_accepts_exact_bounded_synthetic_batch(self):
        status, body = self.post()
        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertEqual(response["results"][q.FIXED_IDS[0]]["result"], "ok")
        self.assertEqual(response["results"][q.FIXED_IDS[1]]["result"], "retry")
        self.assertTrue(self.server.requests[0]["sdk_header_ok"])
        self.assertTrue(self.server.requests[0]["auth_header_ok"])

    def test_unexpected_path_rejected_without_receipt(self):
        status, _ = self.post(url="/not-the-capture-endpoint")
        self.assertEqual(status, 404)
        self.assertEqual(len(self.server.requests), 0)

    def test_invalid_json_is_refused(self):
        status, _ = self.post(raw=b"{not-JSON")
        self.assertEqual(status, 400)
        self.assertTrue(self.server.requests[0]["invalid_envelope"])

    def test_large_request_is_refused(self):
        status, _ = self.post(raw=b" " * 16100)
        self.assertEqual(status, 400)

    def test_third_valid_request_gets_invalid_json_response(self):
        self.post()
        self.post(ids=[q.FIXED_IDS[1]])
        status, raw = self.post(ids=[q.FIXED_IDS[2]])
        self.assertEqual(status, 200)
        with self.assertRaises(ValueError):
            json.loads(raw)

    def test_framework_security_and_release_bits_are_never_upgraded(self):
        bad = q.closed("synthetic failure")
        for key in ("capture_rust_server_qualified", "production_kafka_event_ingestion_qualified",
                    "clickhouse_product_events_qualified", "tenant_authorization_qualified",
                    "dashboard_browser_e2e_qualified", "release_qualified"):
            self.assertFalse(bad[key])

    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": False})
    def test_locked_runtime_required_to_start_any_real_fixture(self, _):
        result = q.qualify_capture_http()
        self.assertFalse(result["real_internal_capture_http_client_qualified"])

if __name__ == "__main__":
    unittest.main()
