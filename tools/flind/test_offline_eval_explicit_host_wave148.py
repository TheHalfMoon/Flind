#!/usr/bin/env python3
"""Wave148: exercise source-owned Pydantic offline-upload settings without app DB.

Compiles the production OfflineEvalSettings class, including validators and
from_env, with real Pydantic on the exact frozen Python runtime.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
import os
from unittest.mock import patch
import unittest
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

ROOT = Path(os.environ.get("FLIND_SOURCE_ROOT", Path(__file__).resolve().parents[2]))


class OfflineUploadError(Exception):
    pass


def production_settings():
    file = ROOT / "products/posthog_ai/eval_harness/offline_results.py"
    tree = ast.parse(file.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "OfflineEvalSettings")
    # Preserve the whole production class, including the complete real
    # validation and from_env logic. No mocking network calls.
    namespace = {
        "BaseModel": BaseModel, "ConfigDict": ConfigDict, "Field": Field,
        "SecretStr": SecretStr, "field_validator": field_validator,
        "ValidationError": ValidationError, "UUID": UUID,
        "__name__": "flind_wave148_real_source", "OfflineUploadError": OfflineUploadError,
        "urlsplit": urlsplit, "os": os,
        "LOOPBACK_HOSTS": frozenset(("localhost", "127.0.0.1", "::1")),
    }
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
    settings_class = namespace["OfflineEvalSettings"]
    namespace["OfflineEvalSettings"] = settings_class
    settings_class.model_rebuild(_types_namespace=namespace)
    return settings_class


SETTINGS = production_settings()
SUITE = SimpleNamespace(
    project_id=123,
    scorer_kinds={"metric": "numeric"},
    scorer_versions={"metric": UUID("00000000-0000-4000-8000-000000000002")},
)


class FlindOfflineDestinationWave148(unittest.TestCase):
    def test_direct_default_never_points_to_upstream(self):
        value = SETTINGS(project_id=123, api_key=SecretStr("fake-only"), scorer_versions=SUITE.scorer_versions)
        self.assertEqual(value.host, "http://127.0.0.1:8010")

    def test_no_api_key_means_no_delivery(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(SETTINGS.from_env(SUITE))

    def test_api_key_alone_fails_closed_before_uploader(self):
        with patch.dict(os.environ, {"POSTHOG_OFFLINE_EVAL_API_KEY": "fake-only"}, clear=True):
            with self.assertRaisesRegex(OfflineUploadError, "FLIND_OFFLINE_EVAL_HOST"):
                SETTINGS.from_env(SUITE)

    def test_explicit_flind_owned_host_wins(self):
        with patch.dict(os.environ, {
            "POSTHOG_OFFLINE_EVAL_API_KEY": "fake-only",
            "POSTHOG_OFFLINE_EVAL_HOST": "https://legacy.example",
            "FLIND_OFFLINE_EVAL_HOST": "https://flind.example",
        }, clear=True):
            item = SETTINGS.from_env(SUITE)
        self.assertIsNotNone(item)
        self.assertEqual(item.host, "https://flind.example")

    def test_explicit_legacy_host_remains_supported(self):
        with patch.dict(os.environ, {
            "POSTHOG_OFFLINE_EVAL_API_KEY": "fake-only",
            "POSTHOG_OFFLINE_EVAL_HOST": "http://127.0.0.1:18010",
        }, clear=True):
            item = SETTINGS.from_env(SUITE)
        self.assertIsNotNone(item)
        self.assertEqual(item.host, "http://127.0.0.1:18010")

    def test_invalid_first_party_host_is_rejected(self):
        for host in ("http://flind.example", "https://user:password@flind.example",
                     "http://localhost.example.com", "https://flind.example/evil"):
            with self.subTest(host=host):
                with patch.dict(os.environ, {
                    "POSTHOG_OFFLINE_EVAL_API_KEY": "fake-only",
                    "FLIND_OFFLINE_EVAL_HOST": host,
                }, clear=True):
                    with self.assertRaises(OfflineUploadError):
                        SETTINGS.from_env(SUITE)

    def test_linked_trace_context_cannot_assume_upstream_host(self):
        text = (ROOT / "products/posthog_ai/eval_harness/harness/lifecycle.py").read_text()
        tree = ast.parse(text)
        contexts = [
            n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "EvalContext"
        ]
        self.assertEqual(len(contexts), 1)
        kwargs = {kw.arg: kw.value for kw in contexts[0].keywords}
        for team, origin in ((0, "https://flind.example"), (88, "https://flind.example")):
            settings = SimpleNamespace(FLIND_HOST=origin, LLM_ANALYTICS_INTERNAL_TEAM_ID=team)
            effective = {}
            for key in ("posthog_trace_host", "posthog_trace_project_id"):
                effective[key] = eval(compile(ast.Expression(kwargs[key]), "<real trace context>", "eval"),
                                      {"settings": settings})
            self.assertEqual(effective["posthog_trace_host"], origin if team > 0 else None)
            self.assertEqual(effective["posthog_trace_project_id"], team if team > 0 else None)


if __name__ == "__main__":
    unittest.main()
