"""Wave104: real Django HTTP session/CSRF qualification must fail closed."""
import unittest
from unittest.mock import patch

from tools.flind import qualify_http_login_wave104 as q


def admitted_child():
    return {
        **{name: True for name in q.FLAGS},
        "framework_http_login_flind_sessionstore_qualified": True,
    }


class FrameworkHttpLoginWave104(unittest.TestCase):
    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": False})
    def test_direct_dependency_lock_required_to_start_pg(self, _lock, postgres):
        result = q.qualify_http_login()
        self.assertFalse(result["framework_http_login_flind_sessionstore_qualified"])
        postgres.assert_not_called()

    @patch.object(q, "prove_django_http_login")
    @patch.object(q, "migrate_auth_and_sessions", return_value={
        "django_framework_auth_session_qualified": False,
    })
    def test_missing_migrations_prevent_login(self, migrations, probe):
        result = q.migrate_then_probe(31245, "private", "private")
        self.assertFalse(result["framework_http_login_flind_sessionstore_qualified"])
        probe.assert_not_called()
        migrations.assert_called_once()

    @patch.object(q, "migrate_auth_and_sessions", return_value={
        "django_framework_auth_session_qualified": True,
    })
    @patch.object(q, "prove_django_http_login", return_value=admitted_child())
    def test_migrations_precede_http_test(self, probe, migrations):
        result = q.migrate_then_probe(31245, "private", "private")
        self.assertTrue(result["framework_http_login_flind_sessionstore_qualified"])
        migrations.assert_called_once_with(31245, "private", "private")
        probe.assert_called_once_with(31245, "private", "private")

    @patch.object(q, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "django_migration_plan": admitted_child(),
    })
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    def test_framework_http_login_success_never_qualifies_product(self, *_):
        result = q.qualify_http_login()
        self.assertTrue(result["framework_http_login_flind_sessionstore_qualified"])
        for key in ("flind_custom_user_login_qualified", "production_middleware_stack_qualified",
                    "product_oauth_qualified", "tenant_authorization_qualified",
                    "browser_playwright_qualified", "release_qualified"):
            self.assertIs(result[key], False)

    @patch.object(q, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "django_migration_plan": {
            **admitted_child(),
            "auth_hostile_origin_rejected": False,
        },
    })
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    def test_any_security_failures_reject_entire_proof(self, *_):
        result = q.qualify_http_login()
        self.assertFalse(result["framework_http_login_flind_sessionstore_qualified"])

    @patch.object(q, "isolated_postgres", return_value={
        "postgres_component_passed": False,
        "django_migration_plan": admitted_child(),
    })
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    def test_false_postgres_claim_never_admits_auth(self, *_):
        result = q.qualify_http_login()
        self.assertFalse(result["framework_http_login_flind_sessionstore_qualified"])

    @patch.object(q, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "django_migration_plan": {},
    })
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    def test_missing_child_receipt_is_closed(self, *_):
        result = q.qualify_http_login()
        self.assertFalse(result["framework_http_login_flind_sessionstore_qualified"])
        self.assertIn("blocker", result)

    def test_no_real_user_or_outbound_api_in_harness(self):
        text = q.__doc__
        self.assertIn("framework auth.User", text)
        self.assertIn("NOT the production Flind custom User", text)
        self.assertEqual(len(q.FLAGS), 10)
        self.assertTrue(all(q.blocked("blocked")[k] is False for k in q.FLAGS))


if __name__ == "__main__":
    unittest.main()
