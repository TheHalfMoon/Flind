"""Wave107: harden bearer-bearing connected-project API target paths.

The actual source validator is executed, and valid forwarded requests traverse a
real loopback HTTP connection using the actual production forward function.
No product database, OAuth credential, live hostname, or deployment required.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import monotonic
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import unquote
import json
import os
import re
import unittest

import requests

from tools.flind.test_outbound_identity_wave102 import actual_function


class UnsafePathError(Exception):
    pass


SAFE_PATH = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@%/-]+$")

UNSAFE_PATHS = (
    "",
    "//evil.example.invalid",
    "../secret",
    "api/../secret",
    "api//admin",
    "api/./admin",
    "http://host.example.invalid/api/",
    "api/%2e%2e/admin",
    "api/%2E%2E/admin",
    "api/%252e%252e/admin",
    "api/%25252e%25252e/admin",
    "api/%252525252e%252525252e/admin",
    "api/%2f%2fevil",
    "api/%255csecret",
    "api/%5csecret",
    "api/%00/secret",
    "api/%0d%0aheader",
    "api/%3Fadmin",
    "api/%23fragment",
    "%68%74%74%70%73%3a%2f%2fevil.com",
    "api/%zz",
    "api/%C0%AE/",
    "api/%E2%82/",
    "api/100%raw",
    "api/" + "a" * 4097,
)

SAFE_PATHS = (
    ("api/projects/2/insights/", "api/projects/2/insights/"),
    ("/api/projects/2/insights/", "api/projects/2/insights/"),
    ("api/projects/2/query/?", None),
    ("api/projects/2/people/%20space/", "api/projects/2/people/%20space/"),
    ("api/projects/2/people/%E2%9C%93/", "api/projects/2/people/%E2%9C%93/"),
    ("api/projects/2/100%25/", "api/projects/2/100%25/"),
    ("api/projects/2/insights/?limit=5", None),
)


def validation_function():
    return actual_function(
        "posthog/api/posthog_connection.py", "_validate_target_path",
        {
            "re": re, "unquote": unquote,
            "ValidationError": UnsafePathError,
            "_SAFE_PATH": SAFE_PATH,
        },
    )


@contextmanager
def private_slot(_connection_id):
    yield True


@dataclass
class ForwardReply:
    status: int
    data: object
    gateway_error: bool = False


class LocalTarget(BaseHTTPRequestHandler):
    server_version = "FlindLocalTest/1"
    sys_version = ""

    def do_GET(self):
        self.server.records.append({
            "path": self.path,
            "bearer_ok": self.headers.get("Authorization") == "Bearer synthetic-test-secret",
            "forward_marker": self.headers.get("X-PostHog-Connection") == "1",
        })
        if self.path == "/api/projects/2/redirect/":
            self.send_response(307)
            self.send_header("Location", "http://127.0.0.1:1/never-follow")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
            return
        raw = json.dumps({"path": self.path, "ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        return


class FlindProjectForwardPathSecurityWave107(unittest.TestCase):
    def test_encoded_traversal_and_scheme_bypass_rejected(self):
        fn = validation_function()
        for raw in UNSAFE_PATHS:
            with self.subTest(raw=raw), self.assertRaises(UnsafePathError):
                fn(raw)

    def test_nonstring_untrusted_paths_are_rejected(self):
        fn = validation_function()
        for raw in (None, 123, ["api/projects/2"], {"path": "api/"}, b"api/"):
            with self.subTest(raw=raw), self.assertRaises(UnsafePathError):
                fn(raw)

    def test_safe_urls_keep_exact_original_encoded_path(self):
        fn = validation_function()
        for raw, expected in SAFE_PATHS:
            with self.subTest(raw=raw):
                if expected is None:
                    with self.assertRaises(UnsafePathError):
                        fn(raw)
                else:
                    self.assertEqual(fn(raw), expected)

    def test_no_unsafe_path_reaches_actual_forwarder(self):
        fn = validation_function()
        with self._private_server() as (srv, forward):
            for raw in UNSAFE_PATHS:
                with self.subTest(raw=raw), self.assertRaises(UnsafePathError):
                    forward(fn(raw))
            self.assertEqual(srv.records, [])

    def test_real_http_preserves_safe_path_and_bearer_marker(self):
        fn = validation_function()
        with self._private_server() as (srv, forward):
            for raw in ("api/projects/2/insights/", "/api/projects/2/insights/",
                        "api/projects/2/people/%20space/", "api/projects/2/100%25/"):
                with self.subTest(raw=raw):
                    valid = fn(raw)
                    reply = forward(valid)
                    self.assertEqual(reply.status, 200)
                    self.assertEqual(reply.data, {"path": "/" + valid, "ok": True})
            self.assertEqual(len(srv.records), 4)
            self.assertTrue(all(x["bearer_ok"] and x["forward_marker"] for x in srv.records))

    def test_real_http_does_not_follow_bearer_redirects(self):
        fn = validation_function()
        with self._private_server() as (srv, forward):
            result = forward(fn("api/projects/2/redirect/"))
            self.assertEqual(result.status, 307)
            self.assertEqual(len(srv.records), 1)
            self.assertTrue(srv.records[0]["bearer_ok"])

    @contextmanager
    def _private_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), LocalTarget)
        server.daemon_threads = True
        server.records = []
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            fn = actual_function(
                "posthog/api/posthog_connection.py", "_forward_through_connection",
                {
                    "requests": requests,
                    "_connection_access_token": lambda _: "synthetic-test-secret",
                    "posthog_connect_base_url": lambda _region:
                        f"http://127.0.0.1:{server.server_port}",
                    "_inflight_slot": private_slot,
                    "CONNECTION_MARKER_HEADER": "X-PostHog-Connection",
                    "SANDBOX_ORIGIN_HEADER": "X-PostHog-Sandbox-Origin",
                    "_METHODS_WITH_BODY": ("POST", "PUT", "PATCH", "DELETE"),
                    "CONNECTION_FORWARD_TIMEOUT_SECONDS": 3,
                    "CONNECTION_MAX_RESPONSE_BYTES": 100_000,
                    "ForwardResult": ForwardReply,
                    "tag_queries": lambda **kwargs: None,
                    "logger": MagicMock(),
                    "json": json,
                    "monotonic": monotonic,
                },
            )
            connection = SimpleNamespace(id=2, config={"region": "US"})
            yield server, lambda path: fn(connection, "GET", path)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=4)


if __name__ == "__main__":
    unittest.main()
