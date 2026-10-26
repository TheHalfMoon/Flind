#!/usr/bin/env python3
"""Wave146: exercise real settings and transactional-email admission, no Django boot.

Verify new Flind instance does not assume an upstream internal project/team.
Do not contact providers or mutate any database.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(os.environ.get("FLIND_SOURCE_ROOT", Path(__file__).resolve().parents[2]))


def setting_value(name: str, environ: dict[str, str]) -> int:
    tree = ast.parse((ROOT / "posthog/settings/base_variables.py").read_text())
    target = next(node.value for node in tree.body if isinstance(node, ast.AnnAssign)
                  and isinstance(node.target, ast.Name) and node.target.id == name)
    def get_from_env(key: str, default: int, *, type_cast=int) -> int:
        return type_cast(environ[key]) if key in environ else default
    return eval(compile(ast.Expression(target), "<real Flind settings>", "eval"),
                {"get_from_env": get_from_env, "int": int})


def real_mail_admission(project_id: int, api_key: str) -> bool:
    tree = ast.parse((ROOT / "posthog/transactional_email.py").read_text())
    func = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "is_transactional_email_configured")
    scope = {"settings": SimpleNamespace(FLIND_HOST="https://flind.example",
                                         POSTHOG_PROJECT_ID=project_id,
                                         POSTHOG_TRANSACTIONAL_EMAIL_API_KEY=api_key)}
    exec(compile(ast.Module(body=[func], type_ignores=[]), "<real mail admission>", "exec"), scope)
    return scope["is_transactional_email_configured"]()


def real_internal_team_id(team_id: int) -> int:
    tree = ast.parse((ROOT / "products/ai_observability/backend/api/personal_spend.py").read_text())
    func = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "_internal_team_id")
    scope = {"settings": SimpleNamespace(LLM_ANALYTICS_INTERNAL_TEAM_ID=team_id)}
    exec(compile(ast.Module(body=[func], type_ignores=[]), "<real internal team consumer>", "exec"), scope)
    return scope["_internal_team_id"]()


class FlindInternalIdsWave146(unittest.TestCase):
    def test_no_inherited_project_id(self):
        project = setting_value("POSTHOG_PROJECT_ID", {})
        self.assertEqual(project, 0)
        self.assertFalse(real_mail_admission(project, "synthetic-only-token"))

    def test_no_inherited_llm_analytics_team(self):
        team = setting_value("LLM_ANALYTICS_INTERNAL_TEAM_ID", {})
        self.assertEqual(team, 0)
        self.assertEqual(real_internal_team_id(team), 0)

    def test_owned_flind_project_id_takes_precedence(self):
        project = setting_value("POSTHOG_PROJECT_ID", {
            "FLIND_PROJECT_ID": "21", "POSTHOG_PROJECT_ID": "2",
        })
        self.assertEqual(project, 21)
        self.assertTrue(real_mail_admission(project, "synthetic-only-token"))
        self.assertFalse(real_mail_admission(project, ""))

    def test_legacy_project_env_explicitly_retained(self):
        project = setting_value("POSTHOG_PROJECT_ID", {"POSTHOG_PROJECT_ID": "31"})
        self.assertEqual(project, 31)
        self.assertTrue(real_mail_admission(project, "synthetic-only-token"))

    def test_owned_internal_team_can_be_configured(self):
        team = setting_value("LLM_ANALYTICS_INTERNAL_TEAM_ID", {
            "FLIND_LLM_ANALYTICS_INTERNAL_TEAM_ID": "44"
        })
        self.assertEqual(team, 44)
        self.assertEqual(real_internal_team_id(team), 44)

    def test_nonpositive_project_blocks_mail_even_with_api_key(self):
        self.assertFalse(real_mail_admission(-1, "synthetic-only-token"))
        self.assertFalse(real_mail_admission(0, "synthetic-only-token"))


if __name__ == "__main__":
    unittest.main()
