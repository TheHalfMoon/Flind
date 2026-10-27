"""Wave147: bounded Git-blob loader and fail-closed sparse Django qualifier."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.qualify_sparse_django_registry_wave147 import (
    GitTrackedPythonFinder,
    GitBlobBatchReader,
    git_offline_env,
    local_missing_resource,
    index_tracked_python,
    probe,
)


class Wave147(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-git-python-fixture-")
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True, timeout=10)
        (self.root / "products" / "mini").mkdir(parents=True)
        (self.root / "products" / "mini" / "__init__.py").write_text("IDENTITY = 'Flind'\n")
        (self.root / "products" / "mini" / "module.py").write_text("VALUE = 42\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True, timeout=10)
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.email=flind@example.invalid",
             "-c", "user.name=Flind Test", "commit", "-qm", "source fixture"],
            check=True, timeout=10,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_only_tracked_source_names(self):
        paths = index_tracked_python(self.root, "HEAD")
        self.assertIn("products/mini/module.py", paths)
        self.assertNotIn("products/mini/secret.txt", paths)

    def test_imports_package_without_materializing_files(self):
        # Deliberately delete the working-tree files. Committed Git blobs remain.
        for p in (self.root / "products" / "mini").glob("*.py"):
            p.unlink()
        finder = GitTrackedPythonFinder(self.root, "HEAD", index_tracked_python(self.root, "HEAD"))
        spec = finder.find_spec("products.mini")
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.IDENTITY, "Flind")
        self.assertEqual(finder.loaded, 1)
        self.assertEqual(finder.last_traced_source, "products/mini/__init__.py")
        self.assertFalse((self.root / "products" / "mini" / "__init__.py").exists())

    def test_rejects_unsafe_module_identifiers_and_foreign_sources(self):
        finder = GitTrackedPythonFinder(self.root, "HEAD", index_tracked_python(self.root, "HEAD"))
        self.assertIsNone(finder.find_spec("products../escape"))
        self.assertIsNone(finder.find_spec("subprocess"))
        self.assertIsNone(finder.find_spec("products.missing"))

    def test_import_limit_fails_before_extra_git_reads(self):
        paths = index_tracked_python(self.root, "HEAD")
        finder = GitTrackedPythonFinder(self.root, "HEAD", paths, limit=1)
        spec = finder.find_spec("products.mini")
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with self.assertRaises(ImportError):
            next_spec = finder.find_spec("products.mini.module")
            assert next_spec is not None and next_spec.loader is not None
            next_spec.loader.exec_module(importlib.util.module_from_spec(next_spec))

    def test_batch_admission_enforces_adjusted_bounded_import_cap(self):
        with self.assertRaises(ValueError):
            GitTrackedPythonFinder(self.root, "HEAD", set(), limit=3001)

    def test_actual_registry_boot_requires_more_than_previous_1200_cap(self):
        self.assertIsInstance(GitTrackedPythonFinder(
            self.root, "HEAD", set(), limit=2200
        ), GitTrackedPythonFinder)

    def test_invalid_source_ref_or_limit_fails_closed(self):
        with self.assertRaises(ValueError):
            index_tracked_python(self.root, "--bad-ref")
        with self.assertRaises(ValueError):
            GitTrackedPythonFinder(self.root, "HEAD", set(), limit=0)
        with self.assertRaises(ValueError):
            GitTrackedPythonFinder(self.root, "HEAD", set(), deadline=9999)


    def test_all_git_reads_disable_partial_clone_lazy_fetch(self):
        self.assertEqual(git_offline_env()["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(git_offline_env()["GIT_TERMINAL_PROMPT"], "0")
        run_real = subprocess.run
        seen = []

        def audit_git_command(*args, **kwargs):
            if isinstance(args[0], list) and args[0][0] == "git":
                seen.append(args[0])
                self.assertEqual(kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
                self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            return run_real(*args, **kwargs)

        with patch("tools.flind.qualify_sparse_django_registry_wave147.subprocess.run",
                   side_effect=audit_git_command):
            paths = index_tracked_python(self.root, "HEAD")
            finder = GitTrackedPythonFinder(self.root, "HEAD", paths)
            spec = finder.find_spec("products.mini")
            assert spec is not None and spec.loader is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertEqual(mod.IDENTITY, "Flind")
        self.assertEqual(len(seen), 2)

    def test_missing_local_blob_reports_only_relative_tracked_source_path(self):
        paths = index_tracked_python(self.root, "HEAD")
        finder = GitTrackedPythonFinder(self.root, "HEAD", paths)
        spec = finder.find_spec("products.mini.module")
        assert spec is not None and spec.loader is not None
        with patch("tools.flind.qualify_sparse_django_registry_wave147.subprocess.run",
                   return_value=subprocess.CompletedProcess(["git", "show"], 128, b"", b"missing")):
            with self.assertRaises(ImportError):
                spec.loader.exec_module(importlib.util.module_from_spec(spec))
        self.assertEqual(finder.last_unavailable_source, "products/mini/module.py")
        self.assertEqual(finder.source_failure_kind, "missing_local_git_blob")

    def test_bounded_local_git_timeout_reports_source_without_network_retry(self):
        paths = index_tracked_python(self.root, "HEAD")
        finder = GitTrackedPythonFinder(self.root, "HEAD", paths)
        spec = finder.find_spec("products.mini")
        assert spec is not None and spec.loader is not None
        with patch("tools.flind.qualify_sparse_django_registry_wave147.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(["git", "show"], 18)):
            with self.assertRaises(ImportError):
                spec.loader.exec_module(importlib.util.module_from_spec(spec))
        self.assertEqual(finder.last_unavailable_source, "products/mini/__init__.py")
        self.assertEqual(finder.source_failure_kind, "bounded_local_git_timeout")

    def test_batch_reader_reuses_one_local_git_process(self):
        with GitBlobBatchReader(self.root, "HEAD") as reader:
            pid = reader.process.pid
            self.assertIn(b"Flind", reader.read("products/mini/__init__.py"))
            self.assertIn(b"VALUE = 42", reader.read("products/mini/module.py"))
            self.assertEqual(reader.process.pid, pid)

    def test_batch_finder_imports_missing_worktree_file_from_git(self):
        for file in (self.root / "products" / "mini").glob("*.py"):
            file.unlink()
        with GitBlobBatchReader(self.root, "HEAD") as reader:
            finder = GitTrackedPythonFinder(
                self.root, "HEAD", index_tracked_python(self.root, "HEAD"),
                batch_reader=reader,
            )
            spec = finder.find_spec("products.mini")
            self.assertIsNotNone(spec)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.IDENTITY, "Flind")
            self.assertEqual(finder.last_traced_source, "products/mini/__init__.py")

    def test_namespace_package_without_init_is_found_in_sparse_checkout(self):
        # Simulate posthog.models.file_system: a tracked directory with Python
        # descendants but no __init__.py and no physical directory in checkout.
        package = self.root / "products" / "namespace_only"
        package.mkdir()
        (package / "module.py").write_text("VALUE = 29\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.email=flind@example.invalid",
             "-c", "user.name=Flind Test", "commit", "-qm", "namespace fixture"],
            check=True,
        )
        (package / "module.py").unlink()
        package.rmdir()
        with GitBlobBatchReader(self.root, "HEAD") as reader:
            finder = GitTrackedPythonFinder(
                self.root, "HEAD", index_tracked_python(self.root, "HEAD"),
                batch_reader=reader,
            )
            spec = finder.find_spec("products.namespace_only")
            self.assertIsNotNone(spec)
            assert spec is not None
            self.assertIsNone(spec.loader)
            self.assertTrue(spec.submodule_search_locations)
            child = finder.find_spec("products.namespace_only.module")
            self.assertIsNotNone(child)
            assert child is not None and child.loader is not None
            module = importlib.util.module_from_spec(child)
            child.loader.exec_module(module)
            self.assertEqual(module.VALUE, 29)
            self.assertFalse(package.exists())

    def test_namespace_root_without_init_in_sparse_checkout(self):
        # Simulate missing top-level 'common' root, backed only by tracked
        # descendants. A normal Python finder cannot see absent directories.
        package = self.root / "common"
        package.mkdir()
        (package / "example.py").write_text("VALUE = 61\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.email=flind@example.invalid",
             "-c", "user.name=Flind Test", "commit", "-qm", "root namespace fixture"],
            check=True,
        )
        (package / "example.py").unlink()
        package.rmdir()
        with GitBlobBatchReader(self.root, "HEAD") as reader:
            finder = GitTrackedPythonFinder(
                self.root, "HEAD", index_tracked_python(self.root, "HEAD"),
                batch_reader=reader,
            )
            spec = finder.find_spec("common")
            self.assertIsNotNone(spec)
            assert spec is not None
            self.assertIsNone(spec.loader)
            child = finder.find_spec("common.example")
            self.assertIsNotNone(child)
            assert child is not None and child.loader is not None
            module = importlib.util.module_from_spec(child)
            child.loader.exec_module(module)
            self.assertEqual(module.VALUE, 61)
            self.assertFalse(package.exists())

    def test_batch_reader_denies_untracked_or_unsafe_paths(self):
        with GitBlobBatchReader(self.root, "HEAD") as reader:
            with self.assertRaises(ImportError):
                reader.read("products/mini/nonexistent.py")
            with self.assertRaises(ValueError):
                reader.read("../unknown.py")

    def test_missing_resource_receipt_uses_only_repository_relative_paths(self):
        inside = self.root / "products" / "growth" / "score.hog"
        err = FileNotFoundError(2, "No such file", str(inside))
        self.assertEqual(local_missing_resource(self.root, err), "products/growth/score.hog")
        outside = FileNotFoundError(2, "No such file", "/tmp/other-project/secret.txt")
        self.assertIsNone(local_missing_resource(self.root, outside))
        self.assertIsNone(local_missing_resource(self.root, FileNotFoundError("no file")))

    def test_no_app_or_release_without_flind_repo(self):
        result = probe(self.root, "HEAD", deadline=3, limit=3)
        self.assertFalse(result["django_registry_qualified"])
        self.assertFalse(result["migrations_qualified"])
        self.assertFalse(result["release_qualified"])


if __name__ == "__main__":
    unittest.main()
