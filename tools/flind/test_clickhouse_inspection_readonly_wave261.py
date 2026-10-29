"""Wave261: run the original Django Command.migrate AST with isolated dependencies.

No Django settings, network, databases, or other PostHog modules are imported.
This tests the *actual method body* from the source file, while all external
dependencies and DB actions are explicit recording mocks.
"""
from __future__ import annotations
import ast
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

SOURCE = Path(__file__).with_name("migrate_clickhouse.py")
if not SOURCE.is_file():
    SOURCE = Path(__file__).resolve().parents[2] / "posthog/management/commands/migrate_clickhouse.py"


def original_migrate_method():
    tree = ast.parse(SOURCE.read_text())
    command = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == "Command")
    method = next(node for node in command.body
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and node.name == "migrate")
    cls = ast.ClassDef(name="OwnerTestCommand", bases=[], keywords=[],
                       body=[method], decorator_list=[])
    mod = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    return compile(mod, str(SOURCE), "exec")


class Wave261ReadOnlyInspectionTests(unittest.TestCase):
    def setUp(self):
        self.database = MagicMock()
        self.database.request_session = SimpleNamespace(auth=None)
        self.create_database = MagicMock()
        self.create_tracking = MagicMock()
        self.creds = SimpleNamespace(user="owner-fixture",
                                     read_password=lambda: "owner-fixture-secret")
        self.creds_fn = MagicMock(return_value=self.creds)
        self.db_fn = MagicMock(return_value=self.database)
        ns = {
            "get_clickhouse_creds": self.creds_fn,
            "ClickHouseUser": SimpleNamespace(MIGRATIONS="migrations"),
            "CLICKHOUSE_DATABASE": "flind_wave261_owner_synthetic",
            "CLICKHOUSE_MIGRATIONS_CLUSTER": "posthog_migrations",
            "Database": self.db_fn,
            "settings": SimpleNamespace(TEST=True, E2E_TESTING=False),
            "_PerRequestPasswordAuth": lambda _: "owner-only-fake-auth",
            "MIGRATIONS_PACKAGE_NAME": "never_import_product_migrations",
        }
        exec(original_migrate_method(), ns)
        self.command = ns["OwnerTestCommand"]()
        self.command._create_database_if_not_exists = self.create_database
        self.command._create_migration_tracking_tables_if_not_exist = self.create_tracking
        self.command.get_migrations = lambda *_: iter([])
        self.command.get_applied_migrations = lambda *_: set()
        self.host = "http://127.0.0.1:18000/"
        self.options = {"upto": 99999, "fake": False, "check": False,
                        "plan": False, "print_sql": False}

    def invoke(self, **overrides):
        opts = {**self.options, **overrides}
        with redirect_stdout(StringIO()):
            self.command.migrate(self.host, opts)

    def assert_read_only(self):
        self.create_database.assert_not_called()
        self.create_tracking.assert_not_called()
        self.creds_fn.assert_called_once_with("migrations")
        self.db_fn.assert_called_once()
        kwargs = self.db_fn.call_args.kwargs
        self.assertIs(kwargs["readonly"], True)
        self.assertIs(kwargs["autocreate"], False)
        self.assertEqual(kwargs["db_url"], self.host)
        self.assertEqual(kwargs["trust_env"], False)
        self.assertEqual(kwargs["cluster"], "posthog_migrations")
        self.assertEqual(self.database.request_session.auth, "owner-only-fake-auth")
        self.database.migrate.assert_not_called()
        self.database.insert.assert_not_called()

    def test_plan_never_creates_database_or_tracking_tables(self):
        self.invoke(plan=True)
        self.assert_read_only()

    def test_check_never_creates_database_or_tracking_tables(self):
        self.invoke(check=True)
        self.assert_read_only()

    def test_plan_plus_check_remains_read_only(self):
        self.invoke(plan=True, check=True, print_sql=True)
        self.assert_read_only()

    def test_non_inspection_apply_path_remains_original_write_path(self):
        self.invoke()
        self.create_database.assert_called_once()
        self.create_tracking.assert_called_once()
        kwargs = self.db_fn.call_args.kwargs
        self.assertIs(kwargs["readonly"], False)
        self.assertIs(kwargs["autocreate"], True)
        self.database.migrate.assert_called_once_with(
            "never_import_product_migrations", 99999, replicated=True
        )

    def test_fake_path_remains_original_write_enabled(self):
        self.invoke(fake=True)
        self.create_database.assert_called_once()
        self.create_tracking.assert_called_once()
        self.assertIs(self.db_fn.call_args.kwargs["readonly"], False)
        self.assertIs(self.db_fn.call_args.kwargs["autocreate"], True)

    def test_missing_database_fails_closed_without_precreating(self):
        self.db_fn.side_effect = RuntimeError("owner_test_database_does_not_exist")
        with self.assertRaisesRegex(RuntimeError, "owner_test_database_does_not_exist"):
            self.invoke(plan=True)
        self.create_database.assert_not_called()
        self.create_tracking.assert_not_called()

    def test_source_has_dedicated_inspection_only_gate(self):
        text = SOURCE.read_text()
        self.assertIn('inspection_only = bool(options["plan"] or options["check"])', text)
        self.assertIn('readonly=inspection_only,', text)
        self.assertIn('autocreate=not inspection_only,', text)
        self.assertNotIn('if options["plan"]:\n            self._create_database', text)


if __name__ == "__main__":
    unittest.main()
