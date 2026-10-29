"""Wave269 native Command.migrate plan/check qualification using all original modules.

Run only inside source-locked owner scratch AFTER authentic Django setup.
The real command and all original migration operations are loaded, but DB,
credentials, and metadata creation are mocked; all sockets are denied by parent.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class NativePlanCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from posthog.management.commands import migrate_clickhouse as migration
        from infi.clickhouse_orm.utils import import_submodules

        cls.migration = migration
        cls.modules = import_submodules("posthog.clickhouse.migrations")
        cls.names = sorted(cls.modules)
        if len(cls.names) != 346:
            raise RuntimeError("W269_NativeModuleCountDrift")

    def execute(self, *, plan=False, check=False, print_sql=False, upto=99999, applied=()):
        from django.core.management.base import CommandError

        module = self.migration
        database = MagicMock(name="read_only_synthetic_database")
        creds = SimpleNamespace(user="wave269_synthetic", read_password=lambda: "not-a-secret")
        credential_lookup = MagicMock(return_value=creds)
        database_builder = MagicMock(return_value=database)
        refuse_create_database = MagicMock(
            side_effect=RuntimeError("W269_DATABASE_CREATE_FORBIDDEN")
        )
        refuse_create_tracking = MagicMock(
            side_effect=RuntimeError("W269_TRACKING_CREATE_FORBIDDEN")
        )
        applied_set = set(applied)
        options = {
            "upto": upto, "fake": False, "plan": plan,
            "check": check, "print_sql": print_sql,
        }
        output = StringIO()
        sys_exit = None
        thrown = None
        with (
            patch.object(module, "get_clickhouse_creds", credential_lookup),
            patch.object(module, "Database", database_builder),
            patch.object(module.Command, "_create_database_if_not_exists", refuse_create_database),
            patch.object(module.Command, "_create_migration_tracking_tables_if_not_exist", refuse_create_tracking),
            patch.object(module.Command, "get_applied_migrations", return_value=applied_set),
            redirect_stdout(output),
        ):
            try:
                module.Command().migrate("http://127.0.0.1:1/", options)
            except SystemExit as exc:
                sys_exit = exc.code
            except CommandError as exc:
                thrown = exc
        refuse_create_database.assert_not_called()
        refuse_create_tracking.assert_not_called()
        database.migrate.assert_not_called()
        database.insert.assert_not_called()
        if thrown is not None:
            credential_lookup.assert_not_called()
            database_builder.assert_not_called()
        else:
            credential_lookup.assert_called_once()
            database_builder.assert_called_once()
            kwargs = database_builder.call_args.kwargs
            self.assertIs(kwargs["readonly"], True)
            self.assertIs(kwargs["autocreate"], False)
            self.assertIs(kwargs["trust_env"], False)
        return output.getvalue(), sys_exit, thrown

    @staticmethod
    def selected(output):
        prefix = "Migration would get applied: "
        return [line.removeprefix(prefix) for line in output.splitlines()
                if line.startswith(prefix)]

    def test_plan_all_346_read_only(self):
        out, exit_code, err = self.execute(plan=True)
        self.assertIsNone(exit_code)
        self.assertIsNone(err)
        self.assertEqual(self.selected(out), self.names)

    def test_check_all_346_exits_one_read_only(self):
        out, exit_code, err = self.execute(check=True)
        self.assertIsNone(err)
        self.assertEqual(exit_code, 1)
        self.assertEqual(self.selected(out), self.names)

    def test_check_with_all_applied_is_up_to_date(self):
        out, exit_code, err = self.execute(check=True, applied=self.names)
        self.assertIsNone(err)
        self.assertIsNone(exit_code)
        self.assertEqual(self.selected(out), [])
        self.assertIn("up to date", out)

    def test_zero_bound_never_includes_first_migration(self):
        out, exit_code, err = self.execute(plan=True, upto=0)
        self.assertIsNone(err)
        self.assertIsNone(exit_code)
        self.assertEqual(self.selected(out), [])

    def test_real_initial_migration_sql_print_only_with_plan(self):
        out, exit_code, err = self.execute(plan=True, upto=1, print_sql=True)
        self.assertIsNone(err)
        self.assertIsNone(exit_code)
        self.assertEqual(self.selected(out), ["0001_initial"])
        self.assertIn("CREATE DATABASE IF NOT EXISTS", out)

    def test_already_applied_filter_preserves_names(self):
        applied = self.names[:35]
        out, exit_code, err = self.execute(plan=True, upto=55, applied=applied)
        self.assertIsNone(err)
        self.assertIsNone(exit_code)
        expected = [n for n in self.names
                    if int(n[:4]) <= 55 and n not in set(applied)]
        self.assertEqual(self.selected(out), expected)

    def test_print_sql_without_plan_fails_before_credentials(self):
        out, exit_code, err = self.execute(print_sql=True)
        self.assertIsNone(exit_code)
        self.assertIsNotNone(err)
        self.assertIn("--print-sql requires --plan", str(err))
        self.assertEqual(out, "")


def run_all() -> None:
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(NativePlanCheckTests)
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if not result.wasSuccessful() or result.testsRun != 7:
        raise RuntimeError(
            f"W269_NATIVE_PLAN_CHECK_TESTS_FAILED: "
            f"{result.testsRun} total; {len(result.failures)} fails; {len(result.errors)} errors"
        )
    print("W269_NATIVE_ORIGINAL_PLAN_CHECK_7_OF_7_PASS", flush=True)
