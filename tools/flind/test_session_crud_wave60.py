"""Synthetic session CRUD must be scoped, rolled back, and non-release."""
import unittest
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from tools.flind import qualify_session_crud_wave60 as run


MIGRATED = {
    "django_framework_auth_session_qualified": True,
    "full_schema_qualified": False,
    "release_qualified": False,
}


class SessionCrudWave60Tests(unittest.TestCase):
    @patch.object(run.subprocess, "run")
    def test_private_transaction_checks_create_update_delete_and_rollback(self, process):
        process.return_value = CompletedProcess(
            [], 0, "BEGIN\nINSERT 0 1\n1\nUPDATE 1\n1\nDELETE 1\n0\nROLLBACK\n0\n", "",
        )
        report = run.prove_session_crud(16222, "private", "flind_ephemeral")
        self.assertTrue(report["session_crud_qualified"])
        self.assertFalse(report["release_qualified"])
        self.assertTrue(report["session_rollback_readback"])
        args = process.call_args.args[0]
        sql = args[-1]
        for operation in ("BEGIN;", "INSERT INTO django_session", "UPDATE django_session",
                          "DELETE FROM django_session", "ROLLBACK;"):
            self.assertIn(operation, sql)
        self.assertEqual(sql.count("SELECT count(*)"), 4)
        self.assertIn("127.0.0.1", args)
        self.assertIn("16222", args)
        self.assertIn("flind_ephemeral", args)
        self.assertNotIn("private", str(report))
        self.assertEqual(process.call_args.kwargs["env"]["PGPASSWORD"], "private")

    @patch.object(run.subprocess, "run")
    def test_any_wrong_receipt_is_not_a_pass(self, process):
        for response in [
            "1\n1\n1\n0\n",
            "1\n0\n0\n0\n",
            "1\n1\n0\n1\n",
            "1\n1\n0\n",
            "",
        ]:
            with self.subTest(response=response):
                process.return_value = CompletedProcess([], 0, response, "")
                result = run.prove_session_crud(16222, "secret", "flind_ephemeral")
                self.assertFalse(result["session_crud_qualified"])

    @patch.object(run.subprocess, "run", return_value=CompletedProcess([], 2, "", "secret"))
    def test_sql_error_does_not_expose_log_or_qualify(self, _process):
        result = run.prove_session_crud(16222, "secret", "flind_ephemeral")
        self.assertFalse(result["session_crud_qualified"])
        self.assertNotIn("secret", str(result))

    @patch.object(run.subprocess, "run", side_effect=TimeoutExpired("psql", 12))
    def test_psql_timeout_is_fail_closed(self, _process):
        result = run.prove_session_crud(16222, "private", "flind_ephemeral")
        self.assertFalse(result["session_crud_qualified"])

    @patch.object(run, "migrate_auth_and_sessions", return_value={
        "django_framework_auth_session_qualified": False,
        "blocker": "Migration timed out",
    })
    @patch.object(run, "prove_session_crud")
    def test_failed_schema_never_runs_session_mutations(self, crud, _migrate):
        report = run.migrate_and_verify(16222, "private", "flind_ephemeral")
        crud.assert_not_called()
        self.assertEqual(report["blocker"], "Migration timed out")
        self.assertFalse(report["session_crud_qualified"])

    @patch.object(run, "migrate_auth_and_sessions", return_value=MIGRATED)
    @patch.object(run, "prove_session_crud", return_value={
        "session_crud_qualified": True,
        "session_rollback_readback": True,
        "release_qualified": False,
    })
    def test_successful_transaction_does_not_grant_release(self, crud, migrate):
        report = run.migrate_and_verify(16222, "secret", "flind_ephemeral")
        self.assertTrue(report["session_crud_qualified"])
        self.assertFalse(report["release_qualified"])
        migrate.assert_called_once()
        crud.assert_called_once()

    @patch.object(run, "audit_runtime_lock", return_value={"direct_lock_qualified": False})
    @patch.object(run, "isolated_postgres")
    def test_unqualified_lock_blocks_postgres(self, postgres, _lock):
        result = run.qualify_session_crud()
        self.assertFalse(result["session_crud_qualified"])
        postgres.assert_not_called()

    @patch.object(run, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(run, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "django_migration_plan": {
            **MIGRATED,
            "session_crud_qualified": True,
            "session_insert_readback": True,
            "session_update_readback": True,
            "session_delete_readback": True,
            "session_rollback_readback": True,
        },
    })
    def test_qualified_session_crud_still_has_no_login_or_release(self, _pg, _lock):
        result = run.qualify_session_crud()
        self.assertTrue(result["framework_schema_qualified"])
        self.assertTrue(result["session_crud_qualified"])
        self.assertFalse(result["custom_user_auth_qualified"])
        self.assertFalse(result["full_schema_qualified"])
        self.assertFalse(result["release_qualified"])

    @patch.object(run, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(run, "isolated_postgres", return_value={
        "postgres_component_passed": False,
        "reason": "Local PostgreSQL toolchain unavailable",
    })
    def test_unavailable_cluster_is_not_a_success(self, _pg, _lock):
        result = run.qualify_session_crud()
        self.assertFalse(result["session_crud_qualified"])
        self.assertIn("PostgreSQL", result["blocker"])


if __name__ == "__main__":
    unittest.main()
