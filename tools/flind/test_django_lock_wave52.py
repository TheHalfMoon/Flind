"""Test Django direct dependency-lock admission without application imports."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.flind import qualify_django_lock as lock


def temporary_manifest(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\n'
        'dependencies = ["django==5.2.18", "redis>=7.0", '
        '"tbb==2022.3.1; sys_platform == \'linux\' and platform_machine == \'x86_64\'"]\n'
    )
    (root / "uv.lock").write_text(
        '[[package]]\nname = "django"\nversion = "5.2.18"\n'
        '[[package]]\nname = "redis"\nversion = "5.3.1"\n'
        '[[package]]\nname = "tbb"\nversion = "2022.3.1"\n'
    )


class DjangoLockWave52Tests(unittest.TestCase):
    def test_source_lock_count_and_platform_marker(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            temporary_manifest(root)
            report = lock.audit_runtime_lock(
                root, installed={"django": "5.2.18", "redis": "5.3.1"},
                sys_platform="darwin", machine="arm64",
            )
        self.assertTrue(report["direct_lock_qualified"])
        self.assertEqual(report["runtime_direct_dependencies"], 3)
        self.assertEqual(report["applicable_direct_dependencies"], 2)
        self.assertEqual(report["installed_locked_direct_dependencies"], 2)
        self.assertEqual(report["platform_excluded"], ["tbb"])
        self.assertFalse(report["django_boot_qualified"])
        self.assertFalse(report["release_qualified"])

    def test_missing_dependency_blocks_qualified_state(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            temporary_manifest(root)
            report = lock.audit_runtime_lock(
                root, installed={"django": "5.2.18"},
                sys_platform="darwin", machine="arm64",
            )
        self.assertEqual(report["missing"], ["redis"])
        self.assertEqual(report["missing_count"], 1)
        self.assertFalse(report["direct_lock_qualified"])

    def test_installed_mismatch_does_not_pass(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            temporary_manifest(root)
            report = lock.audit_runtime_lock(
                root, installed={"django": "5.2.19", "redis": "5.3.1"},
                sys_platform="darwin", machine="arm64",
            )
        self.assertEqual(
            report["version_mismatches"],
            [{"name": "django", "locked": "5.2.18", "installed": "5.2.19"}],
        )
        self.assertFalse(report["direct_lock_qualified"])

    def test_unlocked_direct_dependency_fails_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            temporary_manifest(root)
            (root / "uv.lock").write_text(
                '[[package]]\nname = "django"\nversion = "5.2.18"\n'
            )
            report = lock.audit_runtime_lock(
                root, installed={"django": "5.2.18", "redis": "5.3.1"},
                sys_platform="darwin", machine="arm64",
            )
        self.assertEqual(report["unlocked"], ["redis"])
        self.assertFalse(report["direct_lock_qualified"])

    def test_unknown_marker_never_silently_admits(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            temporary_manifest(root)
            (root / "pyproject.toml").write_text(
                '[project]\n'
                'dependencies = ["django==5.2.18; foo == \'bar\'"]\n'
            )
            report = lock.audit_runtime_lock(
                root, installed={"django": "5.2.18"}, sys_platform="darwin",
            )
        self.assertEqual(report["unverified_markers"], ["django"])
        self.assertFalse(report["direct_lock_qualified"])

    def test_marker_evaluator_rejects_executable_syntax(self):
        for marker in [
            "__import__('os').system('echo unsafe')",
            "sys_platform.__class__ == 'str'",
            "3 > 2",
        ]:
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                lock.marker_matches(marker, sys_platform="darwin", machine="arm64")

    def test_linux_architecture_applies_linux_only_package(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            temporary_manifest(root)
            report = lock.audit_runtime_lock(
                root,
                installed={
                    "django": "5.2.18", "redis": "5.3.1",
                    "tbb": "2022.3.1",
                },
                sys_platform="linux", machine="x86_64",
            )
        self.assertTrue(report["direct_lock_qualified"])
        self.assertEqual(report["applicable_direct_dependencies"], 3)

    def test_canonical_dist_names(self):
        self.assertEqual(lock.canonical("Django_Structlog"), "django-structlog")
        self.assertEqual(lock.canonical("django.structlog"), "django-structlog")

    def test_real_repository_requirements_are_accounted_for(self):
        result = lock.audit_runtime_lock(installed={})
        self.assertGreater(result["applicable_direct_dependencies"], 190)
        self.assertEqual(result["installed_locked_direct_dependencies"], 0)
        self.assertFalse(result["direct_lock_qualified"])
        self.assertFalse(result["release_qualified"])


if __name__ == "__main__":
    unittest.main()
