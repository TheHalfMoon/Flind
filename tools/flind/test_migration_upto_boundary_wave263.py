"""Regression for first-party ClickHouse migration upper-bound handling.

Runs the unmodified get_migrations method body extracted from the original
product Command source. No DB, Django bootstrap, network, or paid services.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "posthog/management/commands/migrate_clickhouse.py"


def original_method():
    tree = ast.parse(SOURCE.read_text())
    command = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Command")
    method = next(node for node in command.body if isinstance(node, ast.FunctionDef) and node.name == "get_migrations")
    # Source method code stays intact; remove only cache decorator to isolate from product imports.
    method.decorator_list = []
    cls = ast.ClassDef(name="OriginalCommand", bases=[], keywords=[], body=[method], decorator_list=[])
    program = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    scope = {"MIGRATIONS_PACKAGE_NAME": "flind_owner_only_synthetic"}
    exec(compile(program, str(SOURCE), "exec"), scope)
    return scope["OriginalCommand"], scope


class MigrationUptoBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.command_type, self.scope = original_method()
        self.names = ["0001_initial", "0004_patch", "0007_followup"]
        self.scope["import_submodules"] = lambda package: {
            name: SimpleNamespace(operations=[name]) for name in reversed(self.names)
        }

    def migrations(self, upto, already_applied=()):
        command = self.command_type()
        command.get_applied_migrations = lambda database: set(already_applied)
        return [name for name, _ in command.get_migrations(object(), upto)]

    def test_zero_bound_does_not_schedule_first_migration(self):
        self.assertEqual(self.migrations(0), [])

    def test_limit_before_first_unapplied_does_not_run_future_migration(self):
        self.assertEqual(self.migrations(4, already_applied=("0001_initial", "0004_patch")), [])

    def test_sparse_numbering_does_not_include_seven_at_limit_five(self):
        self.assertEqual(self.migrations(5), ["0001_initial", "0004_patch"])

    def test_limit_is_inclusive(self):
        self.assertEqual(self.migrations(4), ["0001_initial", "0004_patch"])

    def test_limit_below_second_migration(self):
        self.assertEqual(self.migrations(3), ["0001_initial"])

    def test_applied_migration_is_excluded(self):
        self.assertEqual(self.migrations(4, already_applied=("0001_initial",)), ["0004_patch"])

    def test_unbounded_selection(self):
        self.assertEqual(self.migrations(99999), self.names)


if __name__ == "__main__":
    unittest.main()
