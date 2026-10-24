"""Behavioral tests of CSP cloud source admission, without Django setup."""
import ast
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
CSP = ROOT / "posthog/csp_middleware.py"


def load_flind_js_helper():
    """Compile the actual function AST, no application bootstrap or network."""
    module = ast.parse(CSP.read_text(encoding="utf-8"))
    function = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "flind_js_cloud_sources"
    )
    namespace = {
        "os": os,
        "re": re,
        "urlsplit": urlsplit,
        "settings": SimpleNamespace(SITE_URL="https://app.flind.example"),
    }
    code = compile(ast.fix_missing_locations(
        ast.Module(body=[function], type_ignores=[])
    ), str(CSP), "exec")
    exec(code, namespace)
    return namespace["flind_js_cloud_sources"]


def load_csp_report_helper():
    module = ast.parse(CSP.read_text(encoding="utf-8"))
    function = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "csp_report_endpoint"
    )
    namespace = {
        "urlsplit": urlsplit,
        "urlencode": __import__("urllib.parse", fromlist=["urlencode"]).urlencode,
        "parse_qsl": __import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl,
        "settings": SimpleNamespace(CSP_REPORT_ENDPOINT=None),
        "is_cloud": lambda: True,
    }
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=[function], type_ignores=[])
    ), str(CSP), "exec"), namespace)
    return namespace["csp_report_endpoint"], namespace["settings"]


class BackendCSPWave53Tests(unittest.TestCase):
    def test_readiness_mode_never_queues_sync_tasks_on_app_population(self):
        for file in (
            ROOT / "posthog/apps.py",
            ROOT / "products/mcp_store/backend/apps.py",
        ):
            source = file.read_text()
            self.assertIn('os.environ.get("FLIND_READINESS_CHECK") != "1"', source)
            self.assertIn("queue_sync_", source)

    def test_csp_reports_default_to_disabled_even_in_cloud_mode(self):
        report, settings = load_csp_report_helper()
        self.assertIsNone(settings.CSP_REPORT_ENDPOINT)
        self.assertEqual(report(), "")
        self.assertEqual(report(v="4", distinct_id="patient-data"), "")
        source = CSP.read_text()
        self.assertNotIn("PH_US_API_KEY", source)
        self.assertNotIn("_POSTHOG_CSP_REPORT_ENDPOINT", source)

    def test_explicit_csp_report_url_can_receive_version_parameter(self):
        report, settings = load_csp_report_helper()
        settings.CSP_REPORT_ENDPOINT = "https://app.flind.example/report/?v=2"
        self.assertEqual(
            report(v="4"),
            "https://app.flind.example/report/?v=4",
        )

    def test_imports_no_missing_inherited_csp_constants(self):
        source = CSP.read_text()
        self.assertNotIn("POSTHOG_JS_CLOUD_HOST", source)
        self.assertNotIn("POSTHOG_JS_CLOUD_TOKEN", source)
        self.assertIn("flind_js_cloud_sources()", source)

    def test_no_default_cloud_source_or_config_path(self):
        fn = load_flind_js_helper()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(fn(), ("", "", ""))

    def test_only_explicit_same_origin_https_cloud_js_and_token(self):
        fn = load_flind_js_helper()
        with patch.dict(os.environ, {
            "FLIND_JS_CLOUD_ORIGIN": "https://app.flind.example",
            "FLIND_JS_CLOUD_TOKEN": "project_token-123_A",
        }, clear=True):
            self.assertEqual(
                fn(),
                (
                    "https://app.flind.example",
                    "https://app.flind.example/static/",
                    "https://app.flind.example/array/project_token-123_A/config.js",
                ),
            )

    def test_token_never_leaks_into_csp_when_unsafe(self):
        fn = load_flind_js_helper()
        for token in ("../escape", "a%2Fb", "a?b", "a/b", "a" * 129, ""):
            with self.subTest(token=token), patch.dict(os.environ, {
                "FLIND_JS_CLOUD_ORIGIN": "https://app.flind.example/",
                "FLIND_JS_CLOUD_TOKEN": token,
            }, clear=True):
                origin, static, config = fn()
                self.assertEqual(origin, "https://app.flind.example")
                self.assertEqual(static, "https://app.flind.example/static/")
                self.assertEqual(config, "")

    def test_refuses_vendor_and_lookalike_hosts_and_untrusted_scheme(self):
        fn = load_flind_js_helper()
        urls = [
            "https://us.posthog.com",
            "https://app.flind.example.evil.test",
            "https://evil.example",
            "http://app.flind.example",
            "https://user@app.flind.example",
            "https://app.flind.example:8443",
            "https://app.flind.example/path",
            "https://app.flind.example/?query",
            "https://app.flind.example/#fragment",
            "//app.flind.example",
            "javascript:alert(1)",
            "https://app.flind.example:bad",
            "https://[invalid-ipv6",
        ]
        for raw in urls:
            with self.subTest(raw=raw), patch.dict(
                os.environ, {"FLIND_JS_CLOUD_ORIGIN": raw}, clear=True
            ):
                self.assertEqual(fn(), ("", "", ""))

    def test_no_vendor_default_even_if_old_env_names_are_present(self):
        fn = load_flind_js_helper()
        with patch.dict(os.environ, {
            "POSTHOG_JS_CLOUD_HOST": "https://us.posthog.com",
            "POSTHOG_JS_CLOUD_TOKEN": "vendor-token",
        }, clear=True):
            self.assertEqual(fn(), ("", "", ""))


if __name__ == "__main__":
    unittest.main()
