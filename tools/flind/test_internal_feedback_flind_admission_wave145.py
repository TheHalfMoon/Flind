#!/usr/bin/env python3
"""Wave145: execute actual Flind staff-domain and Slack default expressions.

No Django application boot, network access or third-party provider calls.
The original Django API test is separately strengthened but requires a full
first-party source checkout and test database.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(os.environ.get("FLIND_SOURCE_ROOT", Path(__file__).resolve().parents[2]))


def assignment_value(key: str, env: dict[str, str]) -> str:
    tree = ast.parse((ROOT / "posthog/settings/integrations.py").read_text())
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == key for t in node.targets))
    def get_from_env(name: str, default: str) -> str:
        return env.get(name, default)
    return eval(compile(ast.Expression(assignment.value), "<actual Flind settings>", "eval"),
                {"get_from_env": get_from_env})


def staff_predicate(suffix: str):
    tree = ast.parse((ROOT / "posthog/api/internal_feedback.py").read_text())
    func = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "is_flind_staff_email")
    env: dict[str, object] = {"settings": SimpleNamespace(FLIND_INTERNAL_STAFF_EMAIL_SUFFIX=suffix),
                              "User": object}
    exec(compile(ast.Module(body=[func], type_ignores=[]), "<actual Flind staff predicate>", "exec"), env)
    return env["is_flind_staff_email"]


class Wave145(unittest.TestCase):
    def test_default_staff_domain_is_empty(self):
        self.assertEqual(assignment_value("FLIND_INTERNAL_STAFF_EMAIL_SUFFIX", {}), "")
        self.assertFalse(staff_predicate("")(SimpleNamespace(email="admin@flind.example", is_email_verified=True)))

    def test_default_slack_destination_is_empty(self):
        self.assertEqual(assignment_value("INTERNAL_FEEDBACK_SLACK_CHANNEL", {}), "")
        self.assertEqual(assignment_value("INTERNAL_FEEDBACK_SLACK_BOT_TOKEN", {}), "")

    def test_explicit_first_party_domain_requires_verified_email(self):
        check = staff_predicate("@Flind.Example")
        self.assertTrue(check(SimpleNamespace(email="Team@Flind.Example", is_email_verified=True)))
        self.assertFalse(check(SimpleNamespace(email="team@flind.example", is_email_verified=None)))
        self.assertFalse(check(SimpleNamespace(email="team@flind.example", is_email_verified=False)))
        self.assertFalse(check(SimpleNamespace(email="team@other.example", is_email_verified=True)))
        self.assertFalse(check(SimpleNamespace(email="", is_email_verified=True)))

    def test_malformed_or_unconfigured_suffix_fails_closed(self):
        for value in ("", "flind.example", "@", "bad@@flind.example", 123, None):
            with self.subTest(suffix=value):
                self.assertFalse(staff_predicate(value)(
                    SimpleNamespace(email="team@flind.example", is_email_verified=True)))

    def test_configured_destination_and_api_gates_are_retained(self):
        overrides = {"INTERNAL_FEEDBACK_SLACK_CHANNEL": "C_FLIND_TEST",
                     "INTERNAL_FEEDBACK_SLACK_BOT_TOKEN": "sandbox-only"}
        self.assertEqual(assignment_value("INTERNAL_FEEDBACK_SLACK_CHANNEL", overrides), "C_FLIND_TEST")
        self.assertEqual(assignment_value("INTERNAL_FEEDBACK_SLACK_BOT_TOKEN", overrides), "sandbox-only")
        source = (ROOT / "posthog/api/internal_feedback.py").read_text()
        self.assertIn("permission_classes = [IsAuthenticated, APIScopePermission, IsFlindStaffEmail]", source)
        self.assertIn("if not token or not channel:", source)
        original_test = (ROOT / "posthog/api/test/test_internal_feedback.py").read_text()
        self.assertIn("test_absent_flind_staff_domain_refuses_before_slack", original_test)
        self.assertIn("test_missing_first_party_channel_refuses_without_egress", original_test)


if __name__ == "__main__":
    unittest.main()
