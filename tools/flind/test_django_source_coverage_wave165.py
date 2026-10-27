"""Offline, reproducible Flind Django source coverage regression tests."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.qualify_django_source_coverage_wave165 import (
    available_local_blobs,
    git_env,
    qualify,
    tracked_python,
)


class OfflineSourceCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="flind-source-coverage-")
        self.root = Path(self.temp.name)
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        (self.root / "pyproject.toml").write_text('[project]\nname = "flind"\nversion = "0.1.0"\n')
        for name in ("posthog/__init__.py", "posthog/api/app.py", "products/demo/__init__.py"):
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("# Flind fixture\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.root), "-c", "user.email=test@flind.invalid",
            "-c", "user.name=Flind Test", "commit", "-qm", "fixture",
        ], check=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_full_worktree_tracks_all_paths_without_claiming_release(self):
        result = qualify(self.root)
        self.assertTrue(result["source_coverage_qualified"])
        self.assertEqual(result["tracked_python"], 3)
        self.assertEqual(result["present_in_worktree"], 3)
        self.assertEqual(result["available_only_as_local_git_blob"], 0)
        self.assertEqual(result["unavailable_without_fetch"], 0)
        self.assertFalse(result["django_registry_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_sparse_worktree_uses_local_git_blobs(self):
        (self.root / "posthog/api/app.py").unlink()
        result = qualify(self.root)
        self.assertTrue(result["source_coverage_qualified"])
        self.assertEqual(result["present_in_worktree"], 2)
        self.assertEqual(result["available_only_as_local_git_blob"], 1)
        self.assertEqual(result["unavailable_without_fetch"], 0)

    def test_missing_blob_never_qualifies_and_reports_relative_path(self):
        (self.root / "posthog/api/app.py").unlink()
        with patch("tools.flind.qualify_django_source_coverage_wave165.available_local_blobs", return_value=set()):
            result = qualify(self.root)
        self.assertFalse(result["source_coverage_qualified"])
        self.assertEqual(result["unavailable_without_fetch"], 1)
        self.assertEqual(result["missing_examples"], ["posthog/api/app.py"])
        self.assertFalse(result["release_qualified"])

    def test_git_access_disables_lazy_fetch_and_prompts(self):
        self.assertEqual(git_env()["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(git_env()["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(git_env()["GIT_OPTIONAL_LOCKS"], "0")

    def test_rejects_invalid_ref_or_nonrepo(self):
        with self.assertRaises(ValueError):
            tracked_python(self.root, "--upload-pack=/bad")
        with self.assertRaises(ValueError):
            tracked_python(self.root, "../other")
        with tempfile.TemporaryDirectory() as empty:
            self.assertFalse(qualify(Path(empty))["source_coverage_qualified"])

    def test_batch_check_reports_real_git_blobs(self):
        rows = tracked_python(self.root, "HEAD")
        self.assertEqual(len(rows), 3)
        oids = [oid for oid, _ in rows]
        self.assertEqual(available_local_blobs(self.root, oids), set(oids))


if __name__ == "__main__":
    unittest.main()