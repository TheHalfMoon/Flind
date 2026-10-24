"""Test Flind migration-plan isolation without running Django/SQL or migrations."""
from subprocess import CompletedProcess, TimeoutExpired
import sys
import unittest
from unittest.mock import patch

from tools.flind import qualify_django_pg_plan_wave54 as probe


class DjangoPGPlanWave54Tests(unittest.TestCase):
    @patch.object(probe.subprocess, "run")
    def test_plan_calls_only_showmigrations_on_isolated_db(self, run):
        run.return_value = CompletedProcess(
            [], 0, stdout="[ ]  app.0001_initial\n[ ]  app.0002_next\n", stderr=""
        )
        result = probe.django_readonly_plan(16789, "temporary-password", "flind_ephemeral")
        self.assertTrue(result["django_migration_plan_qualified"])
        self.assertEqual(result["django_migration_plan_entries"], 2)
        self.assertFalse(result["schema_migrated"])
        self.assertFalse(result["release_qualified"])
        args = run.call_args.args[0]
        self.assertEqual(args, [
            sys.executable, "manage.py", "showmigrations", "--plan", "--verbosity", "0"
        ])
        self.assertNotIn("migrate", args)
        env = run.call_args.kwargs["env"]
        self.assertIn("127.0.0.1:16789/flind_ephemeral", env["DATABASE_URL"])
        self.assertIn("temporary-password", env["DATABASE_URL"])
        self.assertEqual(env["FLIND_READINESS_CHECK"], "1")
        self.assertNotIn("temporary-password", str(result))
        self.assertNotIn("temporary-password", str(args))

    @patch.object(probe.subprocess, "run")
    def test_empty_migration_plan_does_not_qualify(self, run):
        run.return_value = CompletedProcess([], 0, stdout="", stderr="")
        result = probe.django_readonly_plan(16789, "test", "flind_ephemeral")
        self.assertFalse(result["django_migration_plan_qualified"])

    @patch.object(probe.subprocess, "run", side_effect=TimeoutExpired("manage.py", 150))
    def test_timeout_fails_closed(self, _run):
        result = probe.django_readonly_plan(16789, "test", "flind_ephemeral")
        self.assertEqual(result["blocker"], "Django migration plan timed out")

    @patch.object(probe, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": False})
    @patch.object(probe, "isolated_postgres")
    def test_missing_python_lock_never_creates_cluster(self, cluster, _audit):
        result = probe.qualify_plan()
        self.assertFalse(result["django_migration_plan_qualified"])
        cluster.assert_not_called()

    @patch.object(probe, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": True})
    @patch.object(probe, "isolated_postgres")
    def test_pg_cluster_result_never_claims_schema_applied(self, cluster, _audit):
        cluster.return_value = {
            "postgres_component_passed": True,
            "django_migration_plan": {
                "django_migration_plan_qualified": True,
                "django_migration_plan_entries": 42,
            },
        }
        result = probe.qualify_plan()
        self.assertTrue(result["django_migration_plan_qualified"])
        self.assertFalse(result["migration_applied"])
        self.assertFalse(result["release_qualified"])
        self.assertIs(cluster.call_args.kwargs["on_ready"], probe.django_readonly_plan)


if __name__ == "__main__":
    unittest.main()
