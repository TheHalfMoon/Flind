"""Wave167: no-network audit of sparse Flind Django runtime resources."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.qualify_django_runtime_assets_wave167 import (
    TRACED_REQUIRED, RUNTIME_SUFFIXES, qualify_assets, tracked_assets,
)


class OfflineAssetCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-asset-test-")
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        (self.root / "pyproject.toml").write_text("[project]\nname = 'flind'\nversion = '0.1.0'\n")
        self.first, self.second = TRACED_REQUIRED
        for path, data in (
            (self.first, "metric()"),
            (self.second, '{"fixture": true}'),
            ("posthog/apps.yml", "name: Flind\n"),
            ("products/growth/backend/app.py", "VALUE=123\n"),
        ):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(data)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root),
                        "-c", "user.email=flind@invalid.example",
                        "-c", "user.name=Flind Tests",
                        "commit", "-qm", "assets fixture"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_release_promotion_even_when_all_assets_are_present(self):
        result = qualify_assets(self.root, scope="all")
        self.assertTrue(result["asset_coverage_qualified"])
        self.assertEqual(result["tracked_candidates"], 3)
        self.assertEqual(result["present_in_worktree"], 3)
        self.assertFalse(result["django_registry_qualified"])
        self.assertFalse(result["migrations_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_traced_scope_is_bounded_to_proven_app_startup_assets(self):
        result = qualify_assets(self.root, scope="traced")
        self.assertEqual(result["tracked_candidates"], 2)
        self.assertTrue(result["asset_coverage_qualified"])
        self.assertEqual(set(result["traced_required_resources"]), set(TRACED_REQUIRED))
        self.assertEqual(result["scope"], "traced")
        self.assertFalse(result["django_registry_qualified"])

    def test_sparse_resource_local_blob_does_not_count_as_materialized(self):
        (self.root / self.first).unlink()
        result = qualify_assets(self.root, scope="all")
        self.assertEqual(result["traced_required_resources"][self.first], "git_blob_only")
        self.assertEqual(result["available_only_as_local_git_blob"], 1)
        self.assertFalse(result["asset_coverage_qualified"])

    def test_missing_blob_fails_closed(self):
        (self.root / self.first).unlink()
        with patch(
            "tools.flind.qualify_django_runtime_assets_wave167.available_local_blobs",
            return_value=set(),
        ):
            result = qualify_assets(self.root, scope="all")
        self.assertEqual(result["traced_required_resources"][self.first], "unavailable")
        self.assertEqual(result["unavailable_without_fetch"], 1)
        self.assertEqual(result["unavailable_examples"], [self.first])
        self.assertFalse(result["asset_coverage_qualified"])

    def test_untracked_missing_dependency_cannot_be_passed(self):
        (self.root / self.second).unlink()
        subprocess.run(["git", "-C", str(self.root), "rm", "--cached", self.second],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(self.root),
                        "-c", "user.email=flind@invalid.example",
                        "-c", "user.name=Flind Tests",
                        "commit", "-qm", "remove resource"], check=True)
        result = qualify_assets(self.root, scope="all")
        self.assertEqual(result["traced_required_resources"][self.second],
                         "not_tracked_at_ref")
        self.assertFalse(result["asset_coverage_qualified"])

    def test_rejects_unsafe_ref_and_does_not_count_python_source(self):
        with self.assertRaises(ValueError):
            tracked_assets(self.root, "--upload-pack=bad")
        with self.assertRaises(ValueError):
            tracked_assets(self.root, "../escape")
        names = [name for _, name in tracked_assets(self.root, "HEAD")]
        self.assertNotIn("products/growth/backend/app.py", names)
        self.assertTrue({".json", ".hog", ".yml"}.issubset(RUNTIME_SUFFIXES))

    def test_non_repository_fails_without_claiming_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = qualify_assets(Path(tmp))
        self.assertFalse(result["asset_coverage_qualified"])
        self.assertFalse(result["release_qualified"])


if __name__ == "__main__":
    unittest.main()