"""Readiness check must not initialize optional GeoIP databases."""
import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock, patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "posthog/geoip.py"


class SimulatedGeoIP2:
    constructed = []

    def __init__(self, *, cache):
        self.cache = cache
        self.constructed.append(cache)


class ReadinessGeoIPWave67Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ast.parse(SRC.read_text(encoding="utf-8"))
        # Execute the actual top-level if gate in isolation without importing
        # the entire GeoIP/Django app dependency graph.
        blocks = [
            node for node in source.body
            if isinstance(node, ast.If)
            and "FLIND_READINESS_CHECK" in ast.unparse(node.test)
        ]
        if len(blocks) != 1:
            raise AssertionError("Expected exactly one readiness GeoIP gate")
        cls.code = compile(
            ast.fix_missing_locations(ast.Module(body=blocks, type_ignores=[])),
            str(SRC), "exec",
        )

    def setUp(self):
        SimulatedGeoIP2.constructed = []

    def execute(self, readiness, geoip_type=SimulatedGeoIP2):
        captured = MagicMock()
        import os
        namespace = {
            "os": os,
            "Optional": Optional,
            "GeoIP2": geoip_type,
            "capture_exception": captured,
        }
        with patch.dict(os.environ, {"FLIND_READINESS_CHECK": readiness}, clear=True):
            exec(self.code, namespace)
        return namespace["geoip"], captured

    def test_readonly_gate_never_reads_geoip_or_reports_false_error(self):
        result, captured = self.execute("1")
        self.assertIsNone(result)
        self.assertEqual(SimulatedGeoIP2.constructed, [])
        captured.assert_not_called()

    def test_production_still_initializes_same_original_geoip_mode(self):
        for value in ("0", ""):
            with self.subTest(value=value):
                result, captured = self.execute(value)
                self.assertIsInstance(result, SimulatedGeoIP2)
                self.assertEqual(result.cache, 8)
                captured.assert_not_called()

    def test_production_missing_database_remains_observable(self):
        class DatabaseNotFound:
            def __init__(self, *, cache):
                raise FileNotFoundError("GeoIP database missing")

        result, captured = self.execute("0", geoip_type=DatabaseNotFound)
        self.assertIsNone(result)
        captured.assert_called_once()
        self.assertIsInstance(captured.call_args.args[0], FileNotFoundError)

    def test_readiness_does_not_initialize_even_a_throwing_provider(self):
        class MustNotTouch:
            def __init__(self, *, cache):
                raise RuntimeError("GeoIP accessed")

        result, captured = self.execute("1", geoip_type=MustNotTouch)
        self.assertIsNone(result)
        captured.assert_not_called()

    def test_app_readiness_env_is_explicit_and_isolated(self):
        boot = (ROOT / "tools/flind/qualify_django_boot_wave53.py").read_text()
        self.assertIn('"FLIND_READINESS_CHECK": "1"', boot)
        self.assertIn('"DATABASE_URL": (', boot)
        self.assertIn('"REDIS_URL": "redis://127.0.0.1:65434/0"', boot)


if __name__ == "__main__":
    unittest.main()
