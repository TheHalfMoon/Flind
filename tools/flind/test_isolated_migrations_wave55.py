"""Verify real migration probe uses only isolated DB and time/disk guardrails."""
import sys
import unittest
from subprocess import CompletedProcess, TimeoutExpired
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tools.flind import qualify_isolated_migrations_wave55 as probe


class IsolatedMigrationsWave55Tests(unittest.TestCase):
    @patch.object(probe.subprocess, "run")
    def test_last_committed_migration_read_from_private_db_only(self, run):
        run.return_value = CompletedProcess(
            [], 0, stdout="posthog|0147_update_tracking\n", stderr=""
        )
        value = probe.read_last_migration(16422, "private-password", "flind_ephemeral")
        self.assertEqual(value, "posthog.0147_update_tracking")
        args = run.call_args.args[0]
        self.assertEqual(args[-2:], [
            "-c", "SELECT app, name FROM django_migrations ORDER BY id DESC LIMIT 1"
        ])
        self.assertIn("127.0.0.1", args)
        self.assertIn("16422", args)
        self.assertEqual(run.call_args.kwargs["env"]["PGPASSWORD"], "private-password")

    @patch.object(probe.subprocess, "run")
    def test_unexpected_receipt_cannot_become_migration_name(self, run):
        for response in ("", "app|name;DROP TABLE users", "a" * 200):
            with self.subTest(response=response):
                run.return_value = CompletedProcess(
                    [], 0, stdout=response, stderr=""
                )
                self.assertIsNone(probe.read_last_migration(16422, "private", "flind_ephemeral"))

    @patch.object(probe, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": False})
    @patch.object(probe, "isolated_postgres")
    def test_incomplete_lock_never_starts_cluster(self, pg, _audit):
        result = probe.qualify_isolated_migrations()
        self.assertFalse(result["isolated_migrations_completed"])
        self.assertFalse(result["release_qualified"])
        pg.assert_not_called()

    @patch.object(probe, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": True})
    @patch.object(probe, "isolated_postgres")
    def test_private_cluster_only_with_callback_and_no_release_claim(self, pg, _audit):
        pg.return_value = {
            "postgres_component_passed": True,
            "django_migration_plan": {
                "isolated_migrations_completed": False,
                "migration_rows_applied_to_disposable_db": 23,
                "blocker": "Postgres extension unavailable",
            },
        }
        report = probe.qualify_isolated_migrations()
        self.assertFalse(report["isolated_migrations_completed"])
        self.assertEqual(report["migration_rows_applied_to_disposable_db"], 23)
        self.assertTrue(report["live_project_schema_untouched"])
        self.assertFalse(report["release_qualified"])
        self.assertTrue(callable(pg.call_args.kwargs["on_ready"]))

    @patch.object(probe, "read_last_migration", return_value="posthog.0001_initial")
    @patch.object(probe, "read_applied_count", return_value=42)
    @patch.object(probe.subprocess, "Popen")
    def test_success_is_only_disposable_db_schema_not_release(self, popen, count, last):
        proc = MagicMock()
        proc.poll.return_value = 0
        proc.returncode = 0
        popen.return_value = proc
        result = probe.attempt_migrations(16379, "random-local-only", "flind_ephemeral")
        self.assertTrue(result["isolated_migrations_completed"])
        self.assertFalse(result["release_qualified"])
        self.assertEqual(result["migration_rows_applied_to_disposable_db"], 42)
        cmd = popen.call_args.args[0]
        self.assertEqual(cmd, [
            sys.executable, "manage.py", "migrate",
            "--noinput", "--database", "default", "--verbosity", "0",
        ])
        env = popen.call_args.kwargs["env"]
        self.assertIn("127.0.0.1:16379/flind_ephemeral", env["DATABASE_URL"])
        self.assertEqual(env["FLIND_READINESS_CHECK"], "1")
        self.assertEqual(env["CLICKHOUSE_HOST"], "127.0.0.1")
        self.assertNotIn("random-local-only", str(result))
        self.assertNotIn("random-local-only", str(cmd))
        count.assert_called_once_with(16379, "random-local-only", "flind_ephemeral")
        self.assertEqual(result["last_committed_migration"], "posthog.0001_initial")

    @patch.object(probe, "read_last_migration", return_value=None)
    @patch.object(probe, "read_applied_count", return_value=0)
    @patch.object(probe.subprocess, "Popen")
    def test_exit_zero_without_migration_receipt_is_not_a_pass(self, popen, count, last):
        proc = MagicMock()
        proc.poll.return_value = 0
        proc.returncode = 0
        popen.return_value = proc
        result = probe.attempt_migrations(16379, "fake", "flind_ephemeral")
        self.assertFalse(result["isolated_migrations_completed"])
        self.assertFalse(result["release_qualified"])

    @patch.object(probe.time, "monotonic", side_effect=[0, 500])
    @patch.object(probe.shutil, "disk_usage",
                  return_value=SimpleNamespace(free=5 * 1024**3))
    @patch.object(probe, "read_last_migration", return_value="posthog.0001_initial")
    @patch.object(probe, "read_applied_count", return_value=1)
    @patch.object(probe.subprocess, "Popen")
    @patch.object(probe.os, "killpg")
    def test_long_running_migrations_are_terminated(self, killpg, popen, *_):
        proc = MagicMock()
        proc.pid = 12346
        proc.poll.side_effect = [None, 1]
        proc.returncode = 1
        popen.return_value = proc
        result = probe.attempt_migrations(16379, "fake", "flind_ephemeral")
        self.assertFalse(result["isolated_migrations_completed"])
        self.assertEqual(result["blocker"], "Migration time limit reached")
        killpg.assert_called_once_with(12346, probe.signal.SIGTERM)

    @patch.object(probe.shutil, "disk_usage",
                  return_value=SimpleNamespace(free=2 * 1024**3))
    @patch.object(probe, "read_last_migration", return_value="posthog.0001_initial")
    @patch.object(probe, "read_applied_count", return_value=1)
    @patch.object(probe.subprocess, "Popen")
    @patch.object(probe.os, "killpg")
    def test_low_disk_forces_child_process_termination(self, killpg, popen, *_):
        proc = MagicMock()
        proc.pid = 12345
        proc.poll.side_effect = [None, 1]
        proc.returncode = 1
        popen.return_value = proc
        result = probe.attempt_migrations(16379, "fake", "flind_ephemeral")
        self.assertFalse(result["isolated_migrations_completed"])
        self.assertEqual(result["blocker"], "Disk safety threshold reached")
        killpg.assert_called_once_with(12345, probe.signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
