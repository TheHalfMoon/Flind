"""Wave172: check migration hydration is offline, bounded, and not a DB migration."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.stage_migration_sources_wave172 import (
    MARKER, MARKER_TEXT, Refusal, stage, git_env, enumerate_migrations,
)


class MigrationSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-migrations-fixture-")
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        (self.repo / "pyproject.toml").write_text('[project]\nname = "flind"\nversion = "0.1.0"\n')
        self.names = [
            "posthog/migrations/__init__.py",
            "posthog/migrations/0001_initial.py",
            "products/demo/backend/migrations/__init__.py",
            "products/demo/backend/migrations/0001_create.py",
        ]
        for name in self.names:
            file = self.repo / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("# synthetic Flind migration source\n")
        (self.repo / "posthog" / "migrations" / "ignored.txt").write_text("ignore")
        (self.repo / "posthog" / "migrations" / "0002_initial copy.py").write_text("copied unimportable")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.repo), "-c", "user.name=Flind Tests",
            "-c", "user.email=flind@invalid.example", "commit", "-qm", "fixture",
        ], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def mark(self):
        (self.repo / MARKER).write_text(MARKER_TEXT)

    def test_preflight_counts_both_top_level_and_nested_sources(self):
        report = stage(self.repo)
        self.assertEqual(report["tracked_migration_files"], 4)
        self.assertEqual(report["tracked_migration_candidates"], 5)
        self.assertEqual(report["noncanonical_migration_count"], 1)
        self.assertEqual(report["noncanonical_migration_paths"], ["posthog/migrations/0002_initial copy.py"])
        self.assertEqual(report["local_git_objects_verified"], 4)
        self.assertEqual(report["physically_present_before"], 4)
        self.assertEqual(report["by_root"], {"posthog": 2, "products": 2})
        self.assertEqual(report["files_written"], 0)
        self.assertFalse(report["migration_sources_qualified"])
        self.assertFalse(report["migration_graph_qualified"])
        self.assertFalse(report["migrations_applied_qualified"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual(len(report["source_commit"]), 40)

    def test_marked_checkout_materializes_exact_tracked_sources(self):
        original = {name: (self.repo / name).read_bytes() for name in self.names}
        for name in self.names:
            (self.repo / name).unlink()
        self.mark()
        report = stage(self.repo, materialize=True)
        self.assertTrue(report["migration_sources_qualified"])
        self.assertEqual(report["files_written"], 4)
        for name, data in original.items():
            self.assertEqual((self.repo / name).read_bytes(), data)
        repeated = stage(self.repo, materialize=True)
        self.assertEqual(repeated["files_written"], 0)
        self.assertFalse(repeated["migration_graph_qualified"])

    def test_missing_marker_denies_any_writes(self):
        for name in self.names:
            (self.repo / name).unlink()
        report = stage(self.repo, materialize=True)
        self.assertEqual(report["blocker"], "scratch_marker_missing")
        self.assertFalse((self.repo / self.names[0]).exists())

    def test_existing_conflict_fails_before_all_materialization(self):
        for name in self.names:
            (self.repo / name).unlink()
        last = self.repo / self.names[-1]
        last.parent.mkdir(parents=True, exist_ok=True)
        last.write_text("conflicting")
        self.mark()
        report = stage(self.repo, materialize=True)
        self.assertEqual(report["blocker"], "migration_destination_conflict")
        self.assertFalse((self.repo / self.names[0]).exists())
        self.assertEqual(last.read_text(), "conflicting")

    def test_missing_git_object_rejected_without_fetch(self):
        with patch("tools.flind.stage_migration_sources_wave172.check_blobs",
                   side_effect=Refusal("migration_git_blob_unavailable")):
            report = stage(self.repo, materialize=True)
        self.assertEqual(report["blocker"], "migration_git_blob_unavailable")
        self.assertFalse(report["migration_sources_qualified"])

    def test_rejects_unsafe_ref_and_does_not_import_modules(self):
        with self.assertRaises(Refusal):
            enumerate_migrations(self.repo, "--upload-pack=bad")
        with self.assertRaises(Refusal):
            enumerate_migrations(self.repo, "../escape")
        self.assertEqual(git_env()["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(git_env()["GIT_TERMINAL_PROMPT"], "0")

    def test_real_missing_repository_is_never_qualified(self):
        with tempfile.TemporaryDirectory() as other:
            report = stage(Path(other))
        self.assertFalse(report["migration_sources_qualified"])
        self.assertFalse(report["migration_graph_qualified"])
        self.assertFalse(report["release_qualified"])


if __name__ == "__main__":
    unittest.main()
