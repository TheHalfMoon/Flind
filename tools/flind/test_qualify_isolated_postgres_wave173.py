"""Wave173: tests for scratch-only PostgreSQL admission and migration selection."""
from __future__ import annotations
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tools.flind.qualify_isolated_postgres_wave173 import (
    PG_MARKER, PG_MARKER_TEXT, SOURCE_MARKER, SOURCE_MARKER_TEXT,
    SMOKE_APP, SMOKE_MIGRATION, execute, expected_migration, safe_locations,
)


class CreateModel:
    def __init__(self, fields=None):
        self.fields = fields if fields is not None else [("id", SimpleNamespace(remote_field=None))]


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-wave173-test-")
        self.base = Path(self.tmp.name)
        self.repo = self.base / "source"
        self.data = self.base / "pg"
        self.sock = self.base / "socket"
        for directory in (self.repo, self.data, self.sock):
            directory.mkdir()
        (self.repo / ".git").mkdir()
        (self.repo / "pyproject.toml").write_text("name='flind'")
        (self.repo / SOURCE_MARKER).write_text(SOURCE_MARKER_TEXT)
        (self.data / "PG_VERSION").write_text("17\n")
        (self.data / PG_MARKER).write_text(PG_MARKER_TEXT)
        (self.sock / ".s.PGSQL.65443").write_text("synthetic socket fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def test_refuses_any_cluster_outside_private_tmp(self):
        # Dedicated scratch data must be under /private/tmp on the actual Mac.
        self.assertFalse(safe_locations(
            self.repo, self.data, Path("/tmp"), 65443, "flind_wave173_synthetic"
        ))

    def test_invalid_database_and_port_rejected(self):
        self.assertFalse(safe_locations(self.repo, self.data, self.sock, 5432, "postgres"))
        self.assertFalse(safe_locations(self.repo, self.data, self.sock, 0, "flind_wave173_synthetic"))
        self.assertFalse(safe_locations(self.repo, self.data, self.sock, 65443, "user_customer_db"))

    def test_missing_marker_fails_closed_before_django_import(self):
        (self.data / PG_MARKER).unlink()
        self.assertFalse(safe_locations(
            self.repo, self.data, self.sock, 65443, "flind_wave173_synthetic"
        ))
        report = execute(self.repo, "HEAD", self.data, self.sock, 65443,
                         "flind_wave173_synthetic", apply_rollback=True)
        self.assertEqual(report["blocker"], "ValueError")
        self.assertFalse(report["postgres_readonly_connection_qualified"])
        self.assertFalse(report["one_first_party_apply_qualified"])
        self.assertFalse(report["release_qualified"])

    def test_first_party_migration_selector_does_not_accept_unscoped_ops(self):
        mig = SimpleNamespace(
            dependencies=[], operations=[CreateModel()],
        )
        plan = [(SimpleNamespace(app_label=SMOKE_APP, name=SMOKE_MIGRATION), False)]
        self.assertTrue(expected_migration(mig, plan))
        self.assertFalse(expected_migration(
            SimpleNamespace(dependencies=["other"], operations=[CreateModel()]), plan
        ))
        self.assertFalse(expected_migration(mig, [(plan[0][0], True)]))
        self.assertFalse(expected_migration(
            SimpleNamespace(dependencies=[], operations=[CreateModel([
                ("user", SimpleNamespace(remote_field="unsafe_relation"))
            ])]), plan
        ))
        self.assertFalse(expected_migration(mig, []))

    def test_project_source_and_pg_datadir_cannot_overlap(self):
        nested = self.repo / "postgres-cluster"
        nested.mkdir()
        (nested / "PG_VERSION").write_text("17")
        (nested / PG_MARKER).write_text(PG_MARKER_TEXT)
        self.assertFalse(safe_locations(
            self.repo, nested, self.sock, 65443, "flind_wave173_synthetic"
        ))


if __name__ == "__main__":
    unittest.main()
