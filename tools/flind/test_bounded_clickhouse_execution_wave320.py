#!/usr/bin/env python3
"""Flind source-pinned regression of the ACTIVE Django ClickHouse bounded apply.

Offline AST extraction of the original production Command method; no DB, network,
or application bootstrap. Run normal and -O. Not live migration qualification.
"""
from __future__ import annotations

import ast
import datetime
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest

EXPECTED_COMMAND_BLOB = "711cb55e01a19b16bc8f95478010574654560db3"
SOURCE = Path(os.environ.get(
    "FLIND_COMMAND_SOURCE",
    str(Path(__file__).resolve().parents[2] / "posthog/management/commands/migrate_clickhouse.py"),
))
PACKAGE = "posthog.clickhouse.migrations"
SOURCE_REPO = Path(os.environ.get("FLIND_SOURCE_REPO", str(Path(__file__).resolve().parents[2])))
ORIGINAL_TREE = "23ea2f226e6be4f2caca554b6ef7cd769d61baa0"
ORIGINAL_0050_BLOBS = {
    "0050_add_channel_definitions.py": "38106c7ce779dd1c18172cf52c6205baa7138b56",
    "0050_session_replay_source.py": "ba1ed44fcf8b81f2705266c4430391816b598b08",
}


def attest_and_extract(raw: bytes):
    blob = subprocess.run(
        ["git", "hash-object", "--stdin"], input=raw, capture_output=True, check=True
    ).stdout.decode().strip()
    if blob != EXPECTED_COMMAND_BLOB:
        raise RuntimeError(f"original command source drift: {blob}")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(SOURCE_REPO), *args], text=True).strip()
    if git("rev-parse", "HEAD:posthog/clickhouse/migrations") != ORIGINAL_TREE:
        raise RuntimeError("original migration tree drift")
    for name, expected in ORIGINAL_0050_BLOBS.items():
        path = f"posthog/clickhouse/migrations/{name}"
        if git("rev-parse", f"HEAD:{path}") != expected or git("hash-object", str(SOURCE_REPO / path)) != expected:
            raise RuntimeError(f"original migration source drift: {name}")
    tree = ast.parse(raw.decode("utf-8"))
    command = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Command")
    migrate = next(node for node in command.body if isinstance(node, ast.FunctionDef) and node.name == "migrate")
    calls = [
        node for node in ast.walk(migrate)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
        and node.func.attr == "_apply_migrations_bounded"
    ]
    if len(calls) != 1:
        raise RuntimeError("original Django apply route does not invoke bounded method exactly once")
    method = next(node for node in command.body if isinstance(node, ast.FunctionDef) and node.name == "_apply_migrations_bounded")
    isolated = ast.fix_missing_locations(ast.Module(
        body=[ast.ClassDef(name="Command", bases=[], keywords=[], body=[method], decorator_list=[])],
        type_ignores=[],
    ))
    return isolated


class FakeDB:
    def __init__(self, applied=()):
        self.applied = set(applied)
        self.executed = []
        self.logged = []

    def _get_applied_migrations_and_create_tables(self, package, replicated=False):
        if package != PACKAGE or replicated is not True:
            raise RuntimeError("unexpected migration package or replication")
        return self.applied.copy()

    def insert(self, records):
        self.logged.extend(record.module_name for record in records)
        self.applied.update(record.module_name for record in records)


def fixture(failing=None):
    names = ["0049_log_entries", "0050_add_channel_definitions", "0050_session_replay_source", "0051_session_replay_source_mv_fix"]
    def operation(name):
        def apply(db):
            if name == failing:
                raise RuntimeError("synthetic operation failure")
            db.executed.append(name)
        return SimpleNamespace(apply=apply)
    return {name: SimpleNamespace(operations=[operation(name)]) for name in names}


def run_active(bound, applied=(), failing=None, db=None):
    raw = SOURCE.read_bytes()
    syntax = attest_and_extract(raw)
    modules = fixture(failing)
    namespace = {
        "MIGRATIONS_PACKAGE_NAME": PACKAGE,
        "import_submodules": lambda _: modules,
        "MigrationHistory": lambda **kw: SimpleNamespace(**kw),
        "datetime": datetime,
    }
    exec(compile(syntax, str(SOURCE), "exec"), namespace)
    db = db if db is not None else FakeDB(applied)
    namespace["Command"]()._apply_migrations_bounded(db, bound)
    return db


class ActiveBoundedExecutionTests(unittest.TestCase):
    def test_repeat_upto_49_does_not_execute_0050(self):
        db = run_active(49, ["0049_log_entries"])
        self.assertEqual(db.executed, [])
        self.assertEqual(db.logged, [])

    def test_both_original_0050_modules_apply_at_50(self):
        db = run_active(50, ["0049_log_entries"])
        expected = ["0050_add_channel_definitions", "0050_session_replay_source"]
        self.assertEqual(db.executed, expected)
        self.assertEqual(db.logged, expected)

    def test_resume_partial_0050(self):
        db = run_active(50, ["0049_log_entries", "0050_add_channel_definitions"])
        self.assertEqual(db.executed, ["0050_session_replay_source"])
        self.assertEqual(db.logged, db.executed)

    def test_upto_51_includes_next_migration(self):
        db = run_active(51, ["0049_log_entries"])
        self.assertEqual(db.executed, [
            "0050_add_channel_definitions", "0050_session_replay_source",
            "0051_session_replay_source_mv_fix",
        ])
        self.assertEqual(db.logged, db.executed)

    def test_failed_operation_does_not_record_failed_migration(self):
        db = FakeDB(["0049_log_entries"])
        with self.assertRaisesRegex(RuntimeError, "synthetic operation failure"):
            run_active(50, failing="0050_add_channel_definitions", db=db)
        self.assertEqual(db.executed, [])
        self.assertEqual(db.logged, [])

    def test_invalid_source_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "source drift"):
            attest_and_extract(SOURCE.read_bytes() + b"\n# drift\n")

    def test_upto_zero_skips_all_operations(self):
        db = run_active(0)
        self.assertEqual(db.executed, [])
        self.assertEqual(db.logged, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
