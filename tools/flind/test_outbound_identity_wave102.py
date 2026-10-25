"""Wave 102: run real outbound HTTP header builders without network or database."""
from __future__ import annotations

import ast
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]


def actual_function(path: str, name: str, namespace: dict):
    """Compile actual production function AST; do not substitute a rewritten stub."""
    source = ROOT / path
    funcs = [x for x in ast.parse(source.read_text()).body
             if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == name]
    if len(funcs) != 1:
        raise AssertionError(f"Could not find exact function {name}")
    func = funcs[0]
    func.decorator_list = []
    tree = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        func,
    ], type_ignores=[])
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(source), "exec"), namespace)
    return namespace[name]


@contextmanager
def slot(_id):
    yield True


class FlindFirstPartyOutboundIdentityWave102(unittest.TestCase):
    def forward(self, *, mcp_origin: bool, sandbox_origin: bool = False):
        res = MagicMock()
        res.status_code = 200
        res.headers = {}
        res.iter_content.return_value = [b'{"ok":true}']
        res.__enter__.return_value = res
        transport = MagicMock()
        transport.RequestException = OSError
        transport.request.return_value = res
        ns = {
            "_connection_access_token": lambda integration: "synthetic-private-token",
            "posthog_connect_base_url": lambda region: "https://flind.example.invalid",
            "_inflight_slot": slot,
            "requests": transport,
            "MCP_USER_AGENT_MARKER": "synthetic-mcp-marker",
            "CONNECTION_MARKER_HEADER": "X-PostHog-Connection",
            "SANDBOX_ORIGIN_HEADER": "X-PostHog-Sandbox-Origin",
            "_METHODS_WITH_BODY": ("POST", "PUT", "PATCH", "DELETE"),
            "CONNECTION_FORWARD_TIMEOUT_SECONDS": 30,
            "CONNECTION_MAX_RESPONSE_BYTES": 5 * 1024 * 1024,
            "ForwardResult": lambda **kw: SimpleNamespace(**kw),
            "monotonic": lambda: 100,
            "tag_queries": lambda **kw: None,
            "logger": MagicMock(),
            "json": json,
        }
        fn = actual_function("posthog/api/posthog_connection.py",
                             "_forward_through_connection", ns)
        fake_integration = SimpleNamespace(id=15, config={"region": "DEV"})
        result = fn(fake_integration, "GET", "api/projects/15/events/",
                    mcp_origin=mcp_origin, sandbox_origin=sandbox_origin)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.data, {"ok": True})
        args, kwargs = transport.request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], "https://flind.example.invalid/api/projects/15/events/")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer synthetic-private-token")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(kwargs["stream"])
        self.assertEqual(kwargs["headers"]["X-PostHog-Connection"], "1")
        self.assertEqual("X-PostHog-Sandbox-Origin" in kwargs["headers"], sandbox_origin)
        return kwargs["headers"]

    def test_mcp_forward_uses_first_party_ua_while_preserving_protocol_marker(self):
        headers = self.forward(mcp_origin=True)
        self.assertEqual(headers["User-Agent"], "flind-connection; synthetic-mcp-marker")
        self.assertNotIn("synthetic-private-token", headers["User-Agent"])

    def test_non_mcp_forward_has_no_mcp_user_agent(self):
        headers = self.forward(mcp_origin=False)
        self.assertNotIn("User-Agent", headers)

    def test_sandbox_forward_preserves_origin_contract(self):
        headers = self.forward(mcp_origin=True, sandbox_origin=True)
        self.assertEqual(headers["X-PostHog-Sandbox-Origin"], "1")

    def test_jwks_uses_first_party_ua_without_token(self):
        captured = {}
        def get_document(url, **kwargs):
            captured.update(kwargs)
            return {"keys": []}, None
        class Jwk:
            @staticmethod
            def from_dict(value):
                return None
        class FetchError(Exception): pass
        class ValidationError(Exception): pass
        class AssertionErrorType(Exception): pass
        ns = {
            "fetch_client_json_document": get_document,
            "PyJWKSet": Jwk,
            "CIMDFetchError": FetchError,
            "CIMDValidationError": ValidationError,
            "ClientAssertionError": AssertionErrorType,
            "JWKS_MAX_DOCUMENT_SIZE": 10000,
            "JWKS_MAX_KEYS": 100,
            "logger": MagicMock(),
        }
        fn = actual_function("posthog/api/oauth/client_assertion.py",
                             "_fetch_jwks_document", ns)
        self.assertEqual(fn("https://partner.example.invalid/jwks.json"), {"keys": []})
        self.assertEqual(captured["user_agent"], "Flind-OAuth-JWKS/1.0")
        self.assertFalse(captured["require_identity_url_shape"])

    def test_cimd_default_ua_comes_from_real_function_signature(self):
        mod = ast.parse((ROOT / "posthog/api/oauth/cimd.py").read_text())
        fun = next(x for x in mod.body if isinstance(x, ast.FunctionDef)
                   and x.name == "fetch_client_json_document")
        defaults = {kw.arg: default for kw, default in zip(fun.args.kwonlyargs, fun.args.kw_defaults)}
        self.assertEqual(ast.literal_eval(defaults["user_agent"]), "Flind-CIMD/1.0")
        self.assertEqual(ast.literal_eval(defaults["require_identity_url_shape"]), True)


if __name__ == "__main__":
    unittest.main()
