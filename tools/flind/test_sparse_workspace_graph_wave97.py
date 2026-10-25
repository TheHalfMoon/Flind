"""Wave97: workspace manifests omitted by sparse checkout still count."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.check_workspace_links import load_tracked_package_manifests, inspect_packages


class SparseWorkspaceManifestGateWave97(unittest.TestCase):
    def test_skip_worktree_manifest_is_read_from_index_without_mutating_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "checked" / "package.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"name": "@flind/root", "private": True,
                                        "dependencies": {"@flind/missing-local": "workspace:*"}}))
            missing = root / "unmaterialized" / "package.json"
            def git(cmd, *, cwd):
                self.assertEqual(cwd, root)
                if cmd[1:4] == ["ls-files", "-t", "-z"]:
                    return b"H checked/package.json\0S unmaterialized/package.json\0"
                if cmd[1:] == ["show", ":unmaterialized/package.json"]:
                    return b'{"name":"@flind/missing-local","private":true}'
                self.fail(f"Unexpected git invocation: {cmd!r}")
            with patch("tools.flind.check_workspace_links.subprocess.check_output", side_effect=git) as git_call:
                items = load_tracked_package_manifests(root)
            self.assertEqual(len(items), 2)
            self.assertFalse(missing.exists(), "Sparse audit must never materialize source files")
            self.assertTrue(inspect_packages(items)["workspace_gate_passed"])
            self.assertTrue(inspect_packages(items)["package_identity_gate_passed"])
            self.assertEqual(git_call.call_count, 2)

    def test_non_sparse_missing_manifest_is_not_hidden_by_git(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("tools.flind.check_workspace_links.subprocess.check_output",
                       return_value=b"H intentionally-absent/package.json\0") as git:
                with self.assertRaises(FileNotFoundError):
                    load_tracked_package_manifests(root)
            git.assert_called_once()

    def test_bad_index_content_is_not_silent_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("tools.flind.check_workspace_links.subprocess.check_output",
                       side_effect=[b"S not-present/package.json\0", b"not JSON"]):
                with self.assertRaises(json.JSONDecodeError):
                    load_tracked_package_manifests(root)

    def test_malformed_git_index_status_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("tools.flind.check_workspace_links.subprocess.check_output",
                       return_value=b"weird-manifest-entry\0"):
                with self.assertRaises(ValueError):
                    load_tracked_package_manifests(Path(temp))

    def test_deleted_current_worktree_file_is_not_replaced_by_head(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("tools.flind.check_workspace_links.subprocess.check_output",
                       return_value=b"H deleted/package.json\0"):
                with self.assertRaises(FileNotFoundError):
                    load_tracked_package_manifests(Path(temp))

    def test_existing_worktree_manifest_wins_over_index_blob(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            f = root / "package.json"
            f.write_text('{"name":"@flind/local","private":true}')
            with patch("tools.flind.check_workspace_links.subprocess.check_output",
                       return_value=b"S package.json\0") as git:
                items = load_tracked_package_manifests(root)
            self.assertEqual(items[0][1]["name"], "@flind/local")
            git.assert_called_once()


if __name__ == "__main__":
    unittest.main()
