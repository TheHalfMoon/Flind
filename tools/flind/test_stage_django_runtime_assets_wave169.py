"""Wave 169 — digest-verified offline runtime resources; never modify a source checkout."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.stage_django_runtime_assets_wave169 import (
    DEFAULT_ASSETS, MARKER, MARKER_CONTENT, StagingError, checked_asset, git, stage,
)


class OfflineScratchStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-stage169-")
        self.base = Path(self.tmp.name)
        self.repo = self.base / "source"
        self.repo.mkdir()
        self.scratch = self.base / "scratch"
        self.scratch.mkdir()
        (self.scratch / MARKER).write_text(MARKER_CONTENT)
        self.seed = self.base / "verified-seed"
        self.seed.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        for i, path in enumerate(DEFAULT_ASSETS):
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((f"Flind synthetic fixture {i}\n").encode("utf-8"))
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo),
                        "-c", "user.name=Flind Tests",
                        "-c", "user.email=flind@example.invalid",
                        "commit", "-qm", "synthetic fixture"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_verifies_and_does_not_write(self):
        result = stage(self.repo, self.scratch, list(DEFAULT_ASSETS))
        self.assertEqual(result["files_verified"], 2)
        commit = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True,
        ).strip()
        self.assertEqual(result["source_commit"], commit)
        receipts = result["file_receipts"]
        self.assertEqual(len(receipts), 2)
        self.assertEqual({r["verified_from"] for r in receipts}, {"local_git"})
        self.assertEqual(sum(r["size_bytes"] for r in receipts), result["total_verified_bytes"])
        self.assertEqual(result["files_written"], 0)
        self.assertFalse(result["resource_staging_qualified"])
        self.assertFalse(result["release_qualified"])
        self.assertFalse((self.scratch / DEFAULT_ASSETS[0]).exists())

    def test_materialization_is_exact_and_idempotent(self):
        result = stage(self.repo, self.scratch, list(DEFAULT_ASSETS), materialize=True)
        self.assertTrue(result["resource_staging_qualified"])
        self.assertEqual(result["files_written"], 2)
        self.assertEqual(len(result["file_receipts"]), 2)
        for receipt in result["file_receipts"]:
            raw = (self.repo / receipt["path"]).read_bytes()
            self.assertEqual(receipt["sha256"], __import__("hashlib").sha256(raw).hexdigest())
            self.assertEqual(receipt["size_bytes"], len(raw))
        for name in DEFAULT_ASSETS:
            self.assertEqual((self.scratch / name).read_bytes(), (self.repo / name).read_bytes())
        repeat = stage(self.repo, self.scratch, list(DEFAULT_ASSETS), materialize=True)
        self.assertEqual(repeat["files_written"], 0)
        self.assertEqual(repeat["files_verified"], 2)
        self.assertFalse(repeat["django_registry_qualified"])

    def test_never_overwrites_conflicting_scratch_asset(self):
        destination = self.scratch / DEFAULT_ASSETS[0]
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"conflicting scratch content")
        result = stage(self.repo, self.scratch, list(DEFAULT_ASSETS), materialize=True)
        self.assertEqual(result["blocker"], "existing_scratch_asset_conflicts")
        self.assertEqual(destination.read_bytes(), b"conflicting scratch content")
        self.assertFalse((self.scratch / DEFAULT_ASSETS[1]).exists())

    def test_marker_required_and_source_overlap_denied(self):
        (self.scratch / MARKER).unlink()
        self.assertEqual(stage(self.repo, self.scratch, list(DEFAULT_ASSETS), materialize=True)["blocker"],
                         "scratch_marker_missing")
        (self.repo / MARKER).write_text(MARKER_CONTENT)
        self.assertEqual(stage(self.repo, self.repo, list(DEFAULT_ASSETS), materialize=True)["blocker"],
                         "scratch_overlaps_repository")
        self.assertFalse((self.scratch / DEFAULT_ASSETS[0]).exists())

    def test_missing_seed_fails_without_partially_materializing(self):
        actual_git = git

        def missing_object(repo, args, input_data=None):
            if args[0] == "cat-file":
                raise StagingError("offline_git_unavailable")
            return actual_git(repo, args, input_data)

        with patch("tools.flind.stage_django_runtime_assets_wave169.git", side_effect=missing_object):
            result = stage(self.repo, self.scratch, list(DEFAULT_ASSETS), materialize=True)
        self.assertEqual(result["blocker"], "local_blob_unavailable")
        self.assertFalse((self.scratch / DEFAULT_ASSETS[0]).exists())

    def test_verified_offline_seed_allows_missing_git_blob(self):
        for name in DEFAULT_ASSETS:
            output = self.seed / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes((self.repo / name).read_bytes())
        actual_git = git

        def missing_object(repo, args, input_data=None):
            if args[0] == "cat-file":
                raise StagingError("offline_git_unavailable")
            return actual_git(repo, args, input_data)

        with patch("tools.flind.stage_django_runtime_assets_wave169.git", side_effect=missing_object):
            result = stage(self.repo, self.scratch, list(DEFAULT_ASSETS),
                           seed=self.seed, materialize=True)
        self.assertTrue(result["resource_staging_qualified"])
        self.assertEqual(result["files_written"], 2)
        self.assertEqual({v["verified_from"] for v in result["file_receipts"]}, {"verified_seed"})

    def test_untrusted_seed_hash_mismatch_rejected(self):
        for name in DEFAULT_ASSETS:
            output = self.seed / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"imposter")
        actual_git = git

        def missing_object(repo, args, input_data=None):
            if args[0] == "cat-file":
                raise StagingError("offline_git_unavailable")
            return actual_git(repo, args, input_data)

        with patch("tools.flind.stage_django_runtime_assets_wave169.git", side_effect=missing_object):
            result = stage(self.repo, self.scratch, list(DEFAULT_ASSETS),
                           seed=self.seed, materialize=True)
        self.assertEqual(result["blocker"], "asset_digest_mismatch")
        self.assertFalse((self.scratch / DEFAULT_ASSETS[0]).exists())

    def test_symlink_escape_denied(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.scratch / "products"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation denied by test OS")
        result = stage(self.repo, self.scratch, list(DEFAULT_ASSETS), materialize=True)
        self.assertEqual(result["blocker"], "scratch_symlink_denied")
        self.assertEqual(list(outside.iterdir()), [])

    def test_invalid_paths_refs_count_and_untracked_fail_closed(self):
        for name in ("../escape.json", "/etc/passwd.json", "products/../../x.json",
                     "products/x.exe", "products/token:alternate.json", "products/CON.json",
                     "products/a//b.json", "products/a?b.json", "products/NUL.txt.json"):
            with self.assertRaises(StagingError):
                checked_asset(name)
        cases = [
            (["products/not-in-repo.json"], "HEAD", "asset_not_tracked_at_ref"),
            (list(DEFAULT_ASSETS), "--upload-pack=evil", "invalid_source_ref"),
            ([DEFAULT_ASSETS[0]] * 2, "HEAD", "duplicate_asset"),
            (["products/not-in-repo.json"] * 25, "HEAD", "asset_count_budget_exceeded"),
        ]
        for names, ref, blocked in cases:
            self.assertEqual(stage(self.repo, self.scratch, names, ref=ref)["blocker"], blocked)

    def test_keeps_git_worktree_unmodified(self):
        before = subprocess.check_output(["git", "-C", str(self.repo), "status", "--porcelain"])
        stage(self.repo, self.scratch, list(DEFAULT_ASSETS), materialize=True)
        after = subprocess.check_output(["git", "-C", str(self.repo), "status", "--porcelain"])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
