#!/usr/bin/env python3
"""Wave149: prove real source paths cannot emit analytics to inherited cloud.

This is a no-network unit probe. It compiles actual Flind source functions and
settings expressions into a minimal harness, with all HTTP/SDK calls replaced
by explicit fakes that record attempted side effects.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from unittest.mock import patch
import os
import unittest

ROOT = Path(os.environ.get("FLIND_SOURCE_ROOT", Path(__file__).resolve().parents[2]))


def source(path: str):
    return ast.parse((ROOT / path).read_text())


def real_assignments(env: dict[str, str]):
    tree = source("posthog/ph_client.py")
    namespace = {"os": os, "__name__": "flind_capture_source"}
    statements = [
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in
            {"PH_US_API_KEY", "PH_US_HOST", "PH_EU_API_KEY", "PH_EU_HOST"} for t in n.targets
        )
    ]
    with patch.dict(os.environ, env, clear=True):
        exec(compile(ast.Module(body=statements, type_ignores=[]),
                     "<actual Flind capture settings>", "exec"), namespace)
    return namespace


def function(path: str, name: str, namespace: dict, *, strip_decorators: bool = False):
    tree = source(path)
    node = next(n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    if strip_decorators:
        node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<actual Flind method>", "exec"), namespace)
    return namespace[name]


class FlindCaptureOwnershipWave149(unittest.TestCase):
    def test_all_capture_tokens_and_hosts_default_to_empty(self):
        values = real_assignments({})
        for key in ("PH_US_API_KEY", "PH_US_HOST", "PH_EU_API_KEY", "PH_EU_HOST"):
            self.assertEqual(values[key], "")

    def test_explicit_flind_capture_configuration_only(self):
        env = {
            "FLIND_CAPTURE_US_API_KEY": "test-us-only",
            "FLIND_CAPTURE_US_HOST": "https://flind.example",
            "FLIND_CAPTURE_EU_API_KEY": "test-eu-only",
            "FLIND_CAPTURE_EU_HOST": "https://eu.flind.example",
        }
        values = real_assignments(env)
        self.assertEqual(values["PH_US_API_KEY"], "test-us-only")
        self.assertEqual(values["PH_US_HOST"], "https://flind.example")
        self.assertEqual(values["PH_EU_API_KEY"], "test-eu-only")
        self.assertEqual(values["PH_EU_HOST"], "https://eu.flind.example")

    def test_rejects_original_capture_origins_and_malformed_hosts(self):
        ns = {"urlsplit": urlsplit}
        allow = function("posthog/ph_client.py", "flind_capture_host_allowed", ns)
        for origin in ("", "https://us.i.posthog.com", "https://eu.i.posthog.com",
                       "https://posthog.com", "https://posthog.io", "http://flind.example",
                       "https://user:secret@flind.example", "https://flind.example/path",
                       "https://flind.example?token=x"):
            with self.subTest(origin=origin):
                self.assertFalse(allow(origin))
        for origin in ("https://flind.example", "https://eu.flind.example:443",
                       "http://127.0.0.1:8010", "http://localhost:8010"):
            with self.subTest(origin=origin):
                self.assertTrue(allow(origin))

    def test_unconfigured_client_does_not_construct_sdk_or_export_events(self):
        captured = []
        class SDK:
            def __init__(self, token, **kwargs):
                captured.append((token, kwargs))
        namespace = {
            "PH_US_API_KEY": "", "PH_US_HOST": "",
            "PH_EU_API_KEY": "", "PH_EU_HOST": "",
            "settings": SimpleNamespace(TEST=False, SCOUT_LIVE_TRIALS_PRIVATE_CAPTURE=False),
            "os": os,
        }
        namespace["flind_capture_host_allowed"] = function(
            "posthog/ph_client.py", "flind_capture_host_allowed", {"urlsplit": urlsplit})
        get_client = function("posthog/ph_client.py", "get_client", namespace)
        self.assertIsNone(get_client("US"))
        self.assertIsNone(get_client("EU"))
        namespace["PH_US_API_KEY"] = "fake-only"
        namespace["PH_US_HOST"] = "https://us.i.posthog.com"
        self.assertIsNone(get_client("US"))
        self.assertEqual(captured, [])

    def test_scoped_capture_noop_without_config_does_not_crash(self):
        ns = {
            "contextmanager": contextmanager,
            "get_client": lambda *a, **kw: None,
            "ScopedCapture": lambda client: SimpleNamespace(client=client),
        }
        scoped = function("posthog/ph_client.py", "ph_scoped_capture", ns)
        with scoped() as value:
            self.assertIsNotNone(value)

    def test_sync_flags_refuses_missing_or_unowned_capture_before_http(self):
        attempted = []
        ns = {
            "PH_US_API_KEY": "", "PH_US_HOST": "",
            "flind_capture_host_allowed": lambda url: False,
            "requests": SimpleNamespace(post=lambda *a, **kw: attempted.append((a, kw))),
        }
        sync = function("posthog/management/commands/sync_feature_flags_from_api.py",
                        "sync_feature_flags_from_api", ns)
        with self.assertRaisesRegex(RuntimeError, "Flind-owned"):
            sync("local-test")
        self.assertEqual(attempted, [])

    def test_owned_capture_passes_the_configured_host_to_sdk(self):
        import sys
        attempted = []
        fake_module = SimpleNamespace(
            Posthog=lambda token, **kw: attempted.append((token, kw)) or "configured-client"
        )
        namespace = {
            "PH_US_API_KEY": "owned-test-token", "PH_US_HOST": "https://flind.example",
            "PH_EU_API_KEY": "", "PH_EU_HOST": "",
            "flind_capture_host_allowed": function(
                "posthog/ph_client.py", "flind_capture_host_allowed", {"urlsplit": urlsplit}
            ),
            "settings": SimpleNamespace(TEST=False, SCOUT_LIVE_TRIALS_PRIVATE_CAPTURE=False),
            "os": os,
        }
        fn = function("posthog/ph_client.py", "get_client", namespace)
        with patch.dict(sys.modules, {"posthoganalytics": fake_module}):
            client = fn("US", sync_mode=True)
        self.assertEqual(client, "configured-client")
        self.assertEqual(attempted[0][0], "owned-test-token")
        self.assertEqual(attempted[0][1]["host"], "https://flind.example")
        self.assertTrue(attempted[0][1]["sync_mode"])

    def test_background_capture_disabled_does_not_register_atexit(self):
        import threading
        registered = []
        class Capture:
            def __init__(self, client):
                self.client = client
        ns = {
            "get_client": lambda *a, **kw: None,
            "ScopedCapture": Capture,
            "_background_client": None,
            "_background_client_lock": threading.Lock(),
            "atexit": SimpleNamespace(register=lambda cb: registered.append(cb)),
        }
        fn = function("posthog/ph_client.py", "ph_background_capture", ns)
        result = fn()
        self.assertIsNone(result.client)
        self.assertEqual(registered, [])

    def test_feedback_media_requires_config_before_database(self):
        class DesktopFeedbackUnavailable(Exception):
            pass
        class FakeManager:
            def get(self, *args, **kwargs):
                self_ref.fail("Feedback DB queried with missing project key")
        self_ref = self
        ns = {
            "PH_EU_API_KEY": "", "PH_US_API_KEY": "",
            "get_instance_region": lambda: "US",
            "DesktopFeedbackUnavailable": DesktopFeedbackUnavailable,
            "Team": SimpleNamespace(objects=FakeManager()),
        }
        fn = function("products/surveys/backend/desktop_feedback.py", "_feedback_media_team", ns)
        with self.assertRaisesRegex(DesktopFeedbackUnavailable, "Flind feedback attachments"):
            fn()

    def test_streamlit_cloud_otel_requires_config_before_urls(self):
        class AppRuntimeError(Exception): pass
        ns = {
            "is_cloud": lambda: True, "get_instance_region": lambda: "US",
            "PH_US_HOST": "", "PH_US_API_KEY": "", "PH_EU_HOST": "", "PH_EU_API_KEY": "",
            "flind_capture_host_allowed": lambda h: False,
            "AppRuntimeError": AppRuntimeError,
        }
        fn = function("products/streamlit_apps/backend/logic/app_runtime.py", "_get_otel_logs_config", ns)
        with self.assertRaisesRegex(AppRuntimeError, "Flind-owned"):
            fn("http://localhost:8010")

    def test_usage_reporting_requires_owner_settings_before_sdk(self):
        ns = {
            "PH_US_API_KEY": "", "PH_US_HOST": "",
            "flind_capture_host_allowed": lambda h: False,
            "PostHogClient": lambda *a, **kw: self.fail("SDK constructed without Flind config"),
        }
        fn = function("posthog/tasks/ai_observability_usage_report.py", "get_ph_client",
                      ns, strip_decorators=True)
        with self.assertRaisesRegex(RuntimeError, "Flind-owned"):
            fn()


if __name__ == "__main__":
    unittest.main()
