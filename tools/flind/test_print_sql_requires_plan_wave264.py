"""Wave264 fail-closed invalid ClickHouse migration flag test.

Compile the exact first-party Command.migrate AST with isolated dependencies,
never bootstrapping Django or performing network/database calls.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock


SOURCE = (
    Path(__file__).resolve().parents[2]
    / "posthog/management/commands/migrate_clickhouse.py"
)


class FakeCommandError(Exception):
    pass


def original_migrate():
    tree = ast.parse(SOURCE.read_text())
    command = next(
        item for item in tree.body
        if isinstance(item, ast.ClassDef) and item.name == "Command"
    )
    method = next(
        item for item in command.body
        if isinstance(item, ast.FunctionDef) and item.name == "migrate"
    )
    test_class = ast.ClassDef(
        name="SourceCommand", bases=[], keywords=[],
        body=[method], decorator_list=[]
    )
    code = compile(
        ast.fix_missing_locations(ast.Module(body=[test_class], type_ignores=[])),
        str(SOURCE), "exec"
    )
    get_creds = MagicMock(
        side_effect=RuntimeError("attempted credential lookup, never allowed here")
    )
    env = {"CommandError": FakeCommandError, "get_clickhouse_creds": get_creds,
           "ClickHouseUser": SimpleNamespace(MIGRATIONS="migrations")}
    exec(code, env)
    return env["SourceCommand"](), get_creds


class Wave264PrintSqlGuard(unittest.TestCase):
    def test_apply_with_print_sql_is_rejected_before_credentials(self):
        self.check_invalid(fake=False, check=False)

    def test_fake_with_print_sql_is_rejected_before_credentials(self):
        self.check_invalid(fake=True, check=False)

    def test_check_with_print_sql_is_rejected_before_credentials(self):
        self.check_invalid(fake=False, check=True)

    def check_invalid(self, *, fake, check):
        command, creds = original_migrate()
        options = {
            "upto": 99999, "fake": fake, "check": check,
            "plan": False, "print_sql": True,
        }
        with self.assertRaisesRegex(FakeCommandError, "--print-sql requires --plan"):
            command.migrate("http://127.0.0.1:9999/", options)
        creds.assert_not_called()

    def test_plan_with_print_sql_passes_initial_flag_validation(self):
        command, creds = original_migrate()
        options = {
            "upto": 99999, "fake": False, "check": False,
            "plan": True, "print_sql": True,
        }
        with self.assertRaisesRegex(RuntimeError, "attempted credential lookup"):
            command.migrate("http://127.0.0.1:9999/", options)
        creds.assert_called_once()


if __name__ == "__main__":
    unittest.main()
