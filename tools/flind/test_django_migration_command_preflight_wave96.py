"""Wave 96: preflight Django migration imports before private DB allocation."""
import subprocess
import unittest
from unittest.mock import patch
from tools.flind import qualify_sustained_migrations_wave75 as q


class DjangoMigrationCommandPreflightWave96(unittest.TestCase):
    @patch.object(q, "isolated_boot_environment", return_value={"FLIND_READINESS_CHECK": "1"})
    @patch.object(q.subprocess, "run")
    def test_actual_command_help_discovery_uses_sandboxed_env(self, run, env):
        run.return_value = subprocess.CompletedProcess([], 0, "usage: migrate", "")
        result = q.migration_startup_preflight()
        self.assertEqual(result, {"passed": True})
        run.assert_called_once()
        args = run.call_args
        self.assertEqual(args.args[0][1:], ["manage.py", "help", "migrate"])
        self.assertEqual(args.kwargs["env"], {"FLIND_READINESS_CHECK": "1"})
        self.assertTrue(args.kwargs["capture_output"])
        self.assertLessEqual(args.kwargs["timeout"], 60)

    @patch.object(q.subprocess, "run")
    def test_exception_text_is_never_returned_or_logged(self, run):
        secret = "synthetic-admin-secret"
        run.return_value = subprocess.CompletedProcess(
            [], 1, "", "ModuleNotFoundError: No module named 'flind-" + secret + "'"
        )
        result = q.migration_startup_preflight()
        self.assertFalse(result["passed"])
        self.assertIn("ModuleNotFoundError", result["blocker"])
        self.assertNotIn(secret, str(result))

    @patch.object(q.subprocess, "run", side_effect=subprocess.TimeoutExpired(["manage.py"], 60))
    def test_timeout_sanitized(self, _run):
        receipt = q.migration_startup_preflight()
        self.assertFalse(receipt["passed"])
        self.assertNotIn("Traceback", str(receipt))

    @patch.object(q.subprocess, "run", side_effect=OSError("machine-username-sensitive"))
    def test_os_error_sanitized(self, _run):
        receipt = q.migration_startup_preflight()
        self.assertFalse(receipt["passed"])
        self.assertNotIn("machine-username-sensitive", str(receipt))

    @patch.object(q, "migration_startup_preflight", return_value={
        "passed": False, "blocker": "Django migration command import failed: ModuleNotFoundError"
    })
    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(q.shutil, "disk_usage")
    def test_no_database_is_started_when_django_import_fails(self, disk, lock, postgres, preflight):
        disk.return_value = type("Disk", (), {"free": 15 * 1024**3})()
        result = q.qualify_sustained(rounds=2, seconds=120)
        self.assertFalse(result["django_migration_preflight_passed"])
        self.assertFalse(result["release_qualified"])
        self.assertIn("ModuleNotFoundError", result["blocker"])
        postgres.assert_not_called()
        preflight.assert_called_once()

    @patch.object(q, "migration_startup_preflight")
    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": False})
    @patch.object(q.shutil, "disk_usage")
    def test_unlocked_env_is_refused_before_import_preflight(self, disk, lock, postgres, preflight):
        disk.return_value = type("Disk", (), {"free": 15 * 1024**3})()
        out = q.qualify_sustained()
        self.assertFalse(out["full_schema_migrations_completed"])
        postgres.assert_not_called()
        preflight.assert_not_called()

    @patch.object(q, "migration_startup_preflight", return_value={"passed": True})
    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(q.shutil, "disk_usage")
    def test_successful_preflight_leaves_full_migration_and_release_independent(self, disk, lock, pg, preflight):
        disk.return_value = type("Disk", (), {"free": 15 * 1024**3})()
        pg.return_value = {"postgres_component_passed": True, "django_migration_plan": {
            "full_schema_migrations_completed": False, "rounds_executed": 1,
            "committed_migration_rows": 2300, "blocker": "Timed out",
        }}
        receipt = q.qualify_sustained()
        self.assertTrue(receipt["django_migration_preflight_passed"])
        self.assertFalse(receipt["full_schema_migrations_completed"])
        self.assertFalse(receipt["release_qualified"])
        pg.assert_called_once()


if __name__ == "__main__":
    unittest.main()
