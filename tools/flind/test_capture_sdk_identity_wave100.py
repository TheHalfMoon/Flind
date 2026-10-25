"""Wave 100: actual capture-v1 header builder uses Flind SDK identity.

The producer's header *names* remain capture-rs compatibility contracts until
the paired Rust ingest service can be migrated and tested in one release.
"""
from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "posthog/api/capture.py"
TEST = ROOT / "posthog/api/test/test_capture_internal.py"

class FlindCaptureSdkIdentityWave100(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(CLIENT.read_text(encoding="utf-8"))
        cls.constant = next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                            and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                            and n.targets[0].id == "SDK_INFO")
        method = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_build_v1_headers")
        ns = {"SDK_INFO": cls.constant, "uuid4": uuid4, "datetime": datetime, "UTC": UTC}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(CLIENT), "exec"), ns)
        cls.headers = staticmethod(ns["_build_v1_headers"])

    def test_actual_function_emits_first_party_sdk_identity(self):
        headers = self.headers("flind_synthetic_token", 1)
        self.assertEqual(headers["User-Agent"], "flind-capture-v1-internal/1.0")
        self.assertEqual(headers["PostHog-Sdk-Info"], headers["User-Agent"])
        self.assertNotIn("posthog", headers["User-Agent"].lower())
        self.assertLessEqual(len(headers["PostHog-Sdk-Info"]), 200)

    def test_required_capture_v1_wire_fields_are_not_renamed(self):
        headers = self.headers("synthetic", 2)
        self.assertEqual(headers["Authorization"], "Bearer synthetic")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["PostHog-Attempt"], "2")
        self.assertEqual(len(headers["PostHog-Request-Id"]), 36)
        self.assertIn("T", headers["PostHog-Request-Timestamp"])
        # These header *names* are required by the existing capture-rs parser.
        rust = (ROOT / "rust/capture/src/v1/constants.rs")
        if rust.is_file():
            source = rust.read_text(encoding="utf-8")
            for key in ("PostHog-Sdk-Info", "PostHog-Attempt",
                        "PostHog-Request-Id", "PostHog-Request-Timestamp"):
                self.assertIn('"' + key + '"', source)

    def test_distinct_retry_attempts_and_request_ids(self):
        first = self.headers("synthetic", 1)
        second = self.headers("synthetic", 3)
        self.assertNotEqual(first["PostHog-Request-Id"], second["PostHog-Request-Id"])
        self.assertEqual(second["PostHog-Attempt"], "3")
        self.assertEqual(first["PostHog-Sdk-Info"], second["PostHog-Sdk-Info"])

    def test_actual_capture_tests_expect_new_sdk_value(self):
        original = TEST.read_text(encoding="utf-8")
        self.assertIn('"flind-capture-v1-internal/1.0"', original)
        self.assertNotIn('"posthog-capture-v1-internal/1.0"', original)

    def test_identity_does_not_echo_customer_token(self):
        token = "synthetic-do-not-leak-to-sdk-info"
        headers = self.headers(token, 1)
        self.assertNotIn(token, headers["User-Agent"])
        self.assertNotIn(token, headers["PostHog-Sdk-Info"])
        self.assertEqual(headers["Authorization"], "Bearer " + token)


if __name__ == "__main__":
    unittest.main()
