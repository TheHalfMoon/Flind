"""Synthetic source-extracted regression for zero-bound ClickHouse migrations."""

import ast
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

SOURCE = Path(
    os.environ.get(
        "FLIND_MIGRATE_SOURCE",
        Path(__file__).resolve().parents[2] / "posthog/management/commands/migrate_clickhouse.py",
    )
)


def load_method():
    tree = ast.parse(SOURCE.read_text())
    command_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Command")
    method = next(node for node in command_class.body if isinstance(node, ast.FunctionDef) and node.name == "migrate")
    isolated = ast.Module(
        body=[ast.ClassDef(name="Command", bases=[], keywords=[], body=[method], decorator_list=[])],
        type_ignores=[],
    )
    ast.fix_missing_locations(isolated)
    database_calls = []

    def credentials():
        return SimpleNamespace(user="synthetic", read_password=lambda: "synthetic")

    def database(*args, **kwargs):
        database_calls.append(kwargs)
        return SimpleNamespace(request_session=SimpleNamespace(auth=None), insert=Mock())

    def reject_credentials(*args, **kwargs):
        raise AssertionError("unexpected credentials lookup")

    namespace = {
        "CommandError": ValueError,
        "get_clickhouse_creds": reject_credentials,
        "ClickHouseUser": SimpleNamespace(MIGRATIONS="migrations"),
        "CLICKHOUSE_DATABASE": "flind_synthetic",
        "CLICKHOUSE_MIGRATIONS_CLUSTER": "local",
        "Database": database,
        "settings": SimpleNamespace(TEST=True, E2E_TESTING=False),
        "_PerRequestPasswordAuth": lambda creds: object(),
    }
    exec(compile(isolated, str(SOURCE), "exec"), namespace)
    command = namespace["Command"]()
    command._create_database_if_not_exists = Mock()
    command._create_migration_tracking_tables_if_not_exist = Mock()
    command._apply_migrations_bounded = Mock()
    command.get_migrations = Mock(return_value=[])
    command.get_applied_migrations = Mock(return_value=set())
    return command, namespace, credentials, database_calls


class TestUptoZero(unittest.TestCase):
    def options(self, **changes):
        return {**dict(upto=0, fake=False, plan=False, check=False, print_sql=False), **changes}

    def test_apply_zero_never_touches_credentials_or_database(self):
        command, _, _, database_calls = load_method()
        command.migrate("http://127.0.0.1:8123", self.options())
        command._create_database_if_not_exists.assert_not_called()
        command._create_migration_tracking_tables_if_not_exist.assert_not_called()
        command._apply_migrations_bounded.assert_not_called()
        self.assertEqual(database_calls, [])

    def test_fake_zero_never_touches_credentials_or_database(self):
        command, _, _, database_calls = load_method()
        command.migrate("http://127.0.0.1:8123", self.options(fake=True))
        command._create_database_if_not_exists.assert_not_called()
        command._create_migration_tracking_tables_if_not_exist.assert_not_called()
        self.assertEqual(database_calls, [])

    def test_negative_bound_is_noop(self):
        command, _, _, database_calls = load_method()
        command.migrate("http://127.0.0.1:8123", self.options(upto=-1))
        command._create_database_if_not_exists.assert_not_called()
        self.assertEqual(database_calls, [])

    def test_print_sql_without_plan_still_fails_first(self):
        command, _, _, database_calls = load_method()
        with self.assertRaisesRegex(ValueError, "--print-sql requires --plan"):
            command.migrate("http://127.0.0.1:8123", self.options(print_sql=True))
        command._create_database_if_not_exists.assert_not_called()
        self.assertEqual(database_calls, [])

    def test_positive_bound_preserves_apply_path(self):
        command, namespace, credentials, database_calls = load_method()
        namespace["get_clickhouse_creds"] = lambda *args: credentials()
        command.migrate("http://127.0.0.1:8123", self.options(upto=1))
        command._create_database_if_not_exists.assert_called_once()
        command._create_migration_tracking_tables_if_not_exist.assert_called_once()
        command._apply_migrations_bounded.assert_called_once()
        self.assertTrue(database_calls[0]["autocreate"])

    def test_plan_zero_preserves_readonly_inspection(self):
        command, namespace, credentials, database_calls = load_method()
        namespace["get_clickhouse_creds"] = lambda *args: credentials()
        command.migrate("http://127.0.0.1:8123", self.options(plan=True))
        command._create_database_if_not_exists.assert_not_called()
        command.get_migrations.assert_called_once()
        self.assertTrue(database_calls[0]["readonly"])
        self.assertFalse(database_calls[0]["autocreate"])


if __name__ == "__main__":
    unittest.main()
