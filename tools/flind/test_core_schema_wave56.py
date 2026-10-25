"""Scoped core-schema qualification cannot be mistaken for the full release."""
from subprocess import CompletedProcess, TimeoutExpired
import unittest
from unittest.mock import patch

from tools.flind import qualify_core_schema_wave56 as core
from tools.flind import qualify_isolated_migrations_wave55 as wave55


class CoreSchemaWave56Tests(unittest.TestCase):
    @patch.object(core, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": False})
    @patch.object(core, "isolated_postgres")
    def test_lock_blocks_cluster_creation(self, cluster, _lock):
        result = core.qualify_core_schema()
        self.assertFalse(result["core_schema_qualified"])
        cluster.assert_not_called()

    @patch.object(core.subprocess, "run")
    def test_schema_receipt_uses_private_postgres_and_readonly_sql(self, run):
        run.return_value = CompletedProcess([], 0, "2\n1\n", "")
        result = core.core_schema_receipt(16789, "secret", "flind_ephemeral")
        self.assertEqual(result["contenttypes_applied_migrations"], 2)
        self.assertTrue(result["django_content_type_table_exists"])
        cmd = run.call_args.args[0]
        self.assertIn("127.0.0.1", cmd)
        self.assertIn("16789", cmd)
        self.assertIn("flind_ephemeral", cmd)
        self.assertNotIn("secret", str(result))
        self.assertIn("to_regclass", cmd[-1])

    @patch.object(core.subprocess, "run", return_value=CompletedProcess([], 0, "", ""))
    def test_absent_schema_fails_closed(self, _run):
        result = core.core_schema_receipt(16789, "secret", "flind_ephemeral")
        self.assertFalse(result["django_content_type_table_exists"])

    @patch.object(core, "attempt_migrations",
                  return_value={"isolated_migrations_completed": True})
    @patch.object(core, "core_schema_receipt",
                  return_value={"contenttypes_applied_migrations": 2,
                                "django_content_type_table_exists": True})
    def test_scoped_completed_migrations_only_qualify_core(self, _receipt, migrate):
        result = core.migrate_core_schema(16789, "secret", "flind_ephemeral")
        self.assertTrue(result["core_schema_qualified"])
        self.assertFalse(result["full_schema_qualified"])
        self.assertFalse(result["release_qualified"])
        self.assertEqual(migrate.call_args.kwargs["app_label"], "contenttypes")
        self.assertEqual(migrate.call_args.kwargs["max_seconds"], 155)

    @patch.object(core, "attempt_migrations",
                  return_value={"isolated_migrations_completed": False,
                                "blocker": "Migration time limit reached"})
    @patch.object(core, "core_schema_receipt",
                  return_value={"contenttypes_applied_migrations": 2,
                                "django_content_type_table_exists": True})
    def test_schema_existing_when_command_timed_out_is_not_a_pass(self, *_):
        result = core.migrate_core_schema(16789, "secret", "flind_ephemeral")
        self.assertFalse(result["core_schema_qualified"])
        self.assertEqual(result["blocker"], "Migration time limit reached")

    def test_wave55_rejects_any_unapproved_app_label(self):
        with self.assertRaises(ValueError):
            # The rejection occurs before launching a process.
            wave55.attempt_migrations(16789, "secret", "flind_ephemeral",
                                      app_label="posthog")


if __name__ == "__main__":
    unittest.main()
