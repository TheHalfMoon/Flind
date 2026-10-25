"""PostgreSQL-backed SessionStore must qualify only after real scoped migrations."""
import unittest
from unittest.mock import patch

from tools.flind import qualify_postgres_session_store_wave64 as run


def successful_store():
    result = run.empty_receipt()
    for key in (
        "session_store_postgres_qualified",
        "authenticated_session_created",
        "cross_instance_session_readback",
        "metadata_preserved_on_save",
        "invalid_user_id_unattributed",
        "impersonation_unattributed",
        "session_revocation_readback",
        "expired_session_unreadable",
    ):
        result[key] = True
    return result


class PostgresSessionStoreWave64Tests(unittest.TestCase):
    @patch.object(run, "audit_runtime_lock", return_value={
        "direct_lock_qualified": False,
    })
    @patch.object(run, "isolated_postgres")
    def test_invalid_direct_lock_cannot_start_pg(self, cluster, _audit):
        result = run.qualify_postgres_session_store()
        self.assertFalse(result["session_store_postgres_qualified"])
        self.assertFalse(result["release_qualified"])
        cluster.assert_not_called()

    @patch.object(run, "migrate_auth_and_sessions", return_value={
        "django_framework_auth_session_qualified": False,
        "blocker": "Migration time limit reached",
    })
    @patch.object(run, "prove_session_store")
    def test_no_schema_never_executes_session_mutations(self, store, migrate):
        result = run.migrate_then_probe(16540, "private", "flind_ephemeral")
        store.assert_not_called()
        migrate.assert_called_once_with(16540, "private", "flind_ephemeral")
        self.assertFalse(result["session_store_postgres_qualified"])
        self.assertEqual(result["blocker"], "Migration time limit reached")
        self.assertNotIn("private", str(result))

    @patch.object(run, "migrate_auth_and_sessions", return_value={
        "django_framework_auth_session_qualified": True,
    })
    @patch.object(run, "prove_session_store", side_effect=lambda *_: successful_store())
    def test_schema_must_precede_session_probe(self, store, migrate):
        result = run.migrate_then_probe(16540, "secret", "flind_ephemeral")
        self.assertTrue(result["framework_schema_qualified"])
        self.assertTrue(result["session_store_postgres_qualified"])
        self.assertFalse(result["release_qualified"])
        store.assert_called_once_with(16540, "secret", "flind_ephemeral")
        migrate.assert_called_once()

    @patch.object(run, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(run, "isolated_postgres")
    def test_successful_postgres_store_does_not_qualify_login_or_release(self, pg, _lock):
        pg.return_value = {
            "postgres_component_passed": True,
            "django_migration_plan": {
                **successful_store(),
                "framework_schema_qualified": True,
            },
        }
        result = run.qualify_postgres_session_store()
        self.assertTrue(result["isolated_postgres_passed"])
        self.assertTrue(result["session_store_postgres_qualified"])
        self.assertFalse(result["full_schema_qualified"])
        self.assertFalse(result["real_login_qualified"])
        self.assertFalse(result["release_qualified"])
        self.assertTrue(callable(pg.call_args.kwargs["on_ready"]))

    @patch.object(run, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(run, "isolated_postgres", return_value={
        "postgres_component_passed": False,
        "django_migration_plan": {
            **successful_store(),
            "framework_schema_qualified": True,
        },
    })
    def test_component_failure_cannot_pass_with_inconsistent_child(self, _pg, _lock):
        result = run.qualify_postgres_session_store()
        self.assertFalse(result["session_store_postgres_qualified"])
        self.assertFalse(result["framework_schema_qualified"])
        self.assertFalse(result["release_qualified"])

    @patch.object(run, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(run, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "django_migration_plan": {
            **successful_store(),
            "framework_schema_qualified": False,
        },
    })
    def test_store_cannot_pass_without_independent_framework_schema(self, _pg, _lock):
        report = run.qualify_postgres_session_store()
        self.assertFalse(report["framework_schema_qualified"])
        self.assertFalse(report["session_store_postgres_qualified"])
        self.assertFalse(report["release_qualified"])

    @patch.object(run, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(run, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "django_migration_plan": {},
    })
    def test_missing_child_receipt_fails_closed(self, _pg, _lock):
        result = run.qualify_postgres_session_store()
        self.assertFalse(result["session_store_postgres_qualified"])
        self.assertIn("blocker", result)


if __name__ == "__main__":
    unittest.main()
