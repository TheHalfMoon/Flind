#!/usr/bin/env python3
"""Wave135: verify actual Flind Desktop signup cutoff setting and access functions."""
from __future__ import annotations

import argparse
import ast
from datetime import UTC, datetime
from functools import lru_cache
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest

ROOT = Path(os.environ.get("FLIND_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
REF = "HEAD"


@lru_cache(maxsize=4)
def tracked(path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{REF}:{path}"], text=True, timeout=30
    )


def setting_value(overrides: dict[str, str]) -> str:
    module = ast.parse(tracked("posthog/settings/web.py"))
    node = next(
        item.value for item in module.body
        if isinstance(item, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "DESKTOP_SIGNUP_CUTOFF"
                for target in item.targets)
    )

    def get_from_env(name: str, default: str) -> str:
        return overrides.get(name, default)

    return eval(compile(ast.Expression(body=node), "<actual desktop setting>", "eval"),
                {"get_from_env": get_from_env})


class DesktopAccessResolutionError(Exception):
    pass


def real_access_functions(cutoff: str):
    tree = ast.parse(tracked("products/tasks/backend/access.py"))
    funcs = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in ("_signup_cutoff", "_signed_up_after_cutoff")
    ]
    if len(funcs) != 2:
        raise AssertionError("Real desktop access functions missing")
    namespace = {
        "settings": SimpleNamespace(DESKTOP_SIGNUP_CUTOFF=cutoff),
        "DesktopAccessResolutionError": DesktopAccessResolutionError,
        "datetime": datetime,
        "UTC": UTC,
        "User": object,
    }
    compiled = compile(ast.Module(body=funcs, type_ignores=[]), "<actual desktop access>", "exec")
    exec(compiled, namespace)
    return namespace["_signup_cutoff"], namespace["_signed_up_after_cutoff"]


class Wave135(unittest.TestCase):
    def test_fresh_flind_has_no_rollout_cutoff(self):
        value = setting_value({})
        self.assertEqual(value, "")
        cutoff, after = real_access_functions(value)
        self.assertIsNone(cutoff())
        self.assertFalse(after(SimpleNamespace(date_joined=datetime(2026, 10, 26, tzinfo=UTC))))

    def test_explicit_operator_cutoff_still_gates_join_dates(self):
        value = setting_value({"DESKTOP_SIGNUP_CUTOFF": "2026-10-01T00:00:00+00:00"})
        cutoff, after = real_access_functions(value)
        self.assertEqual(cutoff(), datetime(2026, 10, 1, tzinfo=UTC))
        self.assertFalse(after(SimpleNamespace(date_joined=datetime(2026, 9, 30, tzinfo=UTC))))
        self.assertTrue(after(SimpleNamespace(date_joined=datetime(2026, 10, 1, tzinfo=UTC))))
        self.assertTrue(after(SimpleNamespace(date_joined=datetime(2026, 10, 26, tzinfo=UTC))))

    def test_bad_operator_cutoff_fails_with_explicit_error(self):
        cutoff, _ = real_access_functions(
            setting_value({"DESKTOP_SIGNUP_CUTOFF": "not-a-timestamp"})
        )
        with self.assertRaisesRegex(DesktopAccessResolutionError, "ISO 8601"):
            cutoff()

    def test_explicit_empty_override_remains_disabled(self):
        self.assertEqual(setting_value({"DESKTOP_SIGNUP_CUTOFF": ""}), "")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="HEAD")
    args, rest = parser.parse_known_args()
    REF = args.ref
    unittest.main(argv=[__file__, *rest])
