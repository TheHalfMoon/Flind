"""Guard Flind's persisted session-user association against invalid IDs.

These tests execute the unchanged source function in isolation so the
first-party source suite remains usable without a local database or Django.
A separate real-import smoke is documented and run with frozen Django.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "posthog/session/backend.py"


def load_auth_id_function():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_auth_user_id"]
    if len(selected) != 1:
        raise AssertionError("Expected exactly one real session user-id helper")
    unit = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(unit)
    namespace = {
        "SESSION_KEY": "_auth_user_id",
        "USER_SESSION_FLAG": "_loginas_original",
        "Any": Any,
    }
    exec(compile(unit, str(SOURCE), "exec"), namespace)
    return namespace["_auth_user_id"]


class SessionUserIdWave61Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolve = staticmethod(load_auth_id_function())

    def test_positive_db_bigint_ids_remain_supported(self):
        for raw, expected in [
            ("1", 1),
            ("42", 42),
            ("0007", 7),
            (42, 42),
            ("9223372036854775807", 9223372036854775807),
            (9223372036854775807, 9223372036854775807),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(self.resolve({"_auth_user_id": raw}), expected)

    def test_invalid_or_unsafe_ids_never_appear_on_session_rows(self):
        for raw in [
            True, False, 0, "0", -1, "-1", "+1",
            " 1", "1 ", "1.0", "1e2", "1_0",
            1.4, None, [], {}, ("1",),
            "١٢", "１２", "1\n",
            "9223372036854775808", 9223372036854775808,
            "9" * 10000,
        ]:
            with self.subTest(type=type(raw).__name__, example=str(raw)[:24]):
                self.assertIsNone(self.resolve({"_auth_user_id": raw}))

    def test_unset_user_id_is_anonymous(self):
        self.assertIsNone(self.resolve({}))
        self.assertIsNone(self.resolve({"anything": 123}))

    def test_impersonation_is_never_attributed_even_with_valid_user(self):
        for value in ("1", 1, "9223372036854775807"):
            with self.subTest(value=value):
                self.assertIsNone(self.resolve({
                    "_auth_user_id": value,
                    "_loginas_original": "signed-original-id",
                }))
                self.assertIsNone(self.resolve({
                    "_auth_user_id": value,
                    "_loginas_original": False,
                }))

    def test_bounded_validation_never_parses_extreme_inputs(self):
        # Even when configured for Python's default 4300-digit int conversion
        # limit, a hostile session value should simply remain unattributed.
        self.assertIsNone(self.resolve({"_auth_user_id": "0" * 100000}))
        self.assertIsNone(self.resolve({"_auth_user_id": 10**200}))


if __name__ == "__main__":
    unittest.main()
