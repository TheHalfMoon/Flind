"""Framework auth/session migration qualification is not full app auth."""
import unittest
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from tools.flind import qualify_auth_session_wave59 as wave59
from tools.flind import qualify_isolated_migrations_wave55 as wave55


PASS_RECEIPT = {
    "applied_migrations": {"contenttypes": 2, "auth": 12, "posthog_session": 3},
    "tables_exist": {
        "auth_group": True, "auth_permission": True, "django_session": True,
    },
}


class AuthSessionWave59Tests(unittest.TestCase):
    @patch.object(wave59, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": False})
    @patch.object(wave59, "isolated_postgres")
    def test_missing_exact_lock_prevents_any_cluster(self, cluster, _audit):
        report = wave59.qualify_auth_session()
        self.assertFalse(report["django_framework_auth_session_qualified"])
        cluster.assert_not_called()

    @patch.object(wave59.subprocess, "run")
    def test_receipt_uses_fixed_readonly_local_sql(self, command):
        command.return_value = CompletedProcess([], 0, "2\n12\n3\n1\n1\n1\n", "")
        got = wave59.read_auth_session_receipt(16523, "secret", "flind_ephemeral")
        self.assertEqual(got, PASS_RECEIPT)
        args = command.call_args.args[0]
        self.assertIn("127.0.0.1", args)
        self.assertIn("16523", args)
        self.assertIn("flind_ephemeral", args)
        self.assertIn("to_regclass", args[-1])
        self.assertNotIn("INSERT", args[-1])
        self.assertNotIn("secret", str(got))
        self.assertEqual(command.call_args.kwargs["env"]["PGPASSWORD"], "secret")

    @patch.object(wave59.subprocess, "run")
    def test_invalid_or_partial_sql_receipts_fail_closed(self, run):
        for completed in [
            CompletedProcess([], 1, "", "failed"),
            CompletedProcess([], 0, "2\n12\n1\n1\n1\n", ""),
            CompletedProcess([], 0, "2\n12\n1\n1\n3\n1\n", ""),
            CompletedProcess([], 0, "2\nnotanumber\n", ""),
        ]:
            with self.subTest(completed=completed.stdout):
                run.return_value = completed
                got = wave59.read_auth_session_receipt(
                    16523, "private", "flind_ephemeral"
                )
                self.assertEqual(got["applied_migrations"]["auth"], 0)
                self.assertFalse(any(got["tables_exist"].values()))

    @patch.object(wave59.subprocess, "run", side_effect=TimeoutExpired("psql", 8))
    def test_receipt_timeout_fails_closed(self, _run):
        got = wave59.read_auth_session_receipt(16523, "private", "flind_ephemeral")
        self.assertFalse(any(got["tables_exist"].values()))

    @patch.object(wave59, "read_auth_session_receipt", return_value=PASS_RECEIPT)
    @patch.object(wave59, "attempt_migrations")
    def test_real_migration_commands_scoped_in_one_db(self, migrate, _receipt):
        migrate.return_value = {"isolated_migrations_completed": True}
        report = wave59.migrate_auth_and_sessions(16523, "private", "flind_ephemeral")
        self.assertTrue(report["django_framework_auth_session_qualified"])
        self.assertFalse(report["custom_user_auth_qualified"])
        self.assertFalse(report["full_schema_qualified"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual([call.kwargs["app_label"] for call in migrate.call_args_list],
                         ["auth", "posthog_session"])
        self.assertEqual(len({call.args for call in migrate.call_args_list}), 1)
        for call in migrate.call_args_list:
            self.assertEqual(call.kwargs["max_seconds"], 155)

    @patch.object(wave59, "read_auth_session_receipt", return_value=PASS_RECEIPT)
    @patch.object(wave59, "attempt_migrations", return_value={
        "isolated_migrations_completed": False,
        "blocker": "Migration time limit reached",
    })
    def test_auth_failure_prevents_sessions_attempt(self, migrate, _receipt):
        report = wave59.migrate_auth_and_sessions(16523, "private", "flind_ephemeral")
        self.assertEqual(len(report["stages"]), 1)
        self.assertFalse(report["django_framework_auth_session_qualified"])
        self.assertEqual(report["blocker"], "Migration time limit reached")
        migrate.assert_called_once()

    @patch.object(wave59, "read_auth_session_receipt")
    @patch.object(wave59, "attempt_migrations",
                  return_value={"isolated_migrations_completed": True})
    def test_missing_table_does_not_pass_even_when_commands_succeed(self, _migrate, receipt):
        receipt.return_value = {
            **PASS_RECEIPT, "tables_exist": {
                **PASS_RECEIPT["tables_exist"], "django_session": False,
            },
        }
        result = wave59.migrate_auth_and_sessions(16523, "private", "flind_ephemeral")
        self.assertFalse(result["django_framework_auth_session_qualified"])

    @patch.object(wave59, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": True})
    @patch.object(wave59, "isolated_postgres")
    def test_successful_cluster_still_does_not_qualify_custom_auth(self, cluster, _lock):
        cluster.return_value = {
            "postgres_component_passed": True,
            "django_migration_plan": {
                "django_framework_auth_session_qualified": True,
                "stages": [],
                **PASS_RECEIPT,
            },
        }
        result = wave59.qualify_auth_session()
        self.assertTrue(result["django_framework_auth_session_qualified"])
        self.assertFalse(result["custom_user_auth_qualified"])
        self.assertFalse(result["full_schema_qualified"])
        self.assertFalse(result["release_qualified"])

    @patch.object(wave59, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": True})
    @patch.object(wave59, "isolated_postgres", return_value={
        "postgres_component_passed": False,
        "reason": "Local PostgreSQL toolchain unavailable",
    })
    def test_missing_postgres_is_not_silently_accepted(self, _pg, _lock):
        result = wave59.qualify_auth_session()
        self.assertFalse(result["django_framework_auth_session_qualified"])
        self.assertIn("PostgreSQL", result["blocker"])

    def test_arbitrary_app_target_still_rejected_before_subprocess(self):
        with self.assertRaises(ValueError):
            wave55.attempt_migrations(16523, "private", "flind_ephemeral",
                                      app_label="posthog")


if __name__ == "__main__":
    unittest.main()
