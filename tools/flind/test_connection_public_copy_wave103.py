"""Wave 103: first-party error messages and OpenAPI text for connected projects.

Compile the real source functions, inject only bounded dependencies; no SQL/network.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from tools.flind.test_outbound_identity_wave102 import actual_function, ROOT


SOURCE = ROOT / "posthog/api/posthog_connection.py"


class PublicConnectionIdentityWave103(unittest.TestCase):
    def test_expired_or_missing_token_error_is_flind_owned(self):
        class ValidationError(Exception): pass
        api = SimpleNamespace(access_token_expired=lambda: False)
        fn = actual_function("posthog/api/posthog_connection.py",
                             "_connection_access_token",
                             {"OauthIntegration": lambda _: api, "ValidationError": ValidationError})
        integration = SimpleNamespace(sensitive_config={})
        with self.assertRaisesRegex(ValidationError, "This Flind connection"):
            fn(integration)

    def test_scoped_key_unknown_grant_denied_under_flind_name(self):
        class PermissionDenied(Exception): pass
        fn = actual_function(
            "posthog/api/posthog_connection.py",
            "_enforce_caller_covers_connection_scopes",
            {"get_authenticator_scopes": lambda _: {"integration:read"},
             "PermissionDenied": PermissionDenied}
        )
        request = SimpleNamespace(successful_authenticator=object())
        conn = SimpleNamespace(config={"granted_scopes": []})
        with self.assertRaisesRegex(PermissionDenied, "This Flind connection"):
            fn(request, conn)

    @classmethod
    def view_method(cls, method_name, namespace):
        tree = ast.parse(SOURCE.read_text())
        target_class = next(x for x in tree.body if isinstance(x, ast.ClassDef)
                            and x.name == "PostHogConnectionViewSet")
        funcs = [x for x in target_class.body
                 if isinstance(x, ast.FunctionDef) and x.name == method_name]
        assert len(funcs) == 1
        node = funcs[0]
        node.decorator_list = []
        mod = ast.Module(body=[ast.ImportFrom(module="__future__",
                                             names=[ast.alias(name="annotations")], level=0),
                               node], type_ignores=[])
        ast.fix_missing_locations(mod)
        exec(compile(mod, str(SOURCE), "exec"), namespace)
        return namespace[method_name]

    def test_nested_forward_refused_with_flind_message(self):
        class ValidationError(Exception): pass
        fn = self.view_method("_authorized_connection", {
            "ValidationError": ValidationError,
            "CONNECTION_MARKER_HEADER": "X-PostHog-Connection",
        })
        request = SimpleNamespace(headers={"X-PostHog-Connection": "1"})
        with self.assertRaisesRegex(ValidationError, "through a Flind connection"):
            fn(MagicMock(), request, "42")

    def test_missing_project_connection_does_not_return_legacy_label(self):
        class NotFound(Exception): pass
        fn = self.view_method("_get_connection", {"NotFound": NotFound})
        with self.assertRaisesRegex(NotFound, "No Flind connection"):
            fn(MagicMock(), None)

    def test_openapi_public_metadata_says_flind(self):
        tree = ast.parse(SOURCE.read_text())
        klass = next(x for x in tree.body if isinstance(x, ast.ClassDef)
                     and x.name == "PostHogConnectionViewSet")
        descriptions = []
        for f in klass.body:
            if not isinstance(f, ast.FunctionDef):
                continue
            for deco in f.decorator_list:
                if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name) and deco.func.id == "extend_schema":
                    for kw in deco.keywords:
                        if kw.arg in ("summary", "description") and isinstance(kw.value, ast.Constant):
                            descriptions.append(kw.value.value)
        self.assertEqual(len(descriptions), 4)
        self.assertTrue(all("PostHog" not in desc for desc in descriptions))
        self.assertTrue(any("Flind connection" in desc for desc in descriptions))

    def test_wire_protocol_and_integration_kind_remain_unchanged(self):
        code = SOURCE.read_text()
        self.assertIn('CONNECTION_MARKER_HEADER = "X-PostHog-Connection"', code)
        self.assertIn("POSTHOG_CONNECT_KIND", code)
        self.assertIn("posthog_connect_base_url", code)
        self.assertNotIn("PostHog connection has", code)


if __name__ == "__main__":
    unittest.main()
