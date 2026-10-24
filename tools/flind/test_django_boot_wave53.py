"""Test real Django startup qualification safety without actually starting Django."""
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess, TimeoutExpired
import os
import sys
from tools.flind import qualify_django_boot_wave53 as boot


class DjangoBootWave53Tests(unittest.TestCase):
    def test_isolated_env_drops_ambient_provider_tokens(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "do-not-use",
            "POSTHOG_API_KEY": "do-not-use",
            "AWS_SECRET_ACCESS_KEY": "do-not-use",
            "DATABASE_URL": "postgres://live.example",
        }, clear=False):
            env = boot.isolated_boot_environment()
        for forbidden in ("OPENAI_API_KEY", "POSTHOG_API_KEY", "AWS_SECRET_ACCESS_KEY"):
            self.assertNotIn(forbidden, env)
        self.assertIn("127.0.0.1:65433", env["DATABASE_URL"])
        self.assertIn("127.0.0.1:65434", env["REDIS_URL"])
        self.assertGreaterEqual(len(env["SECRET_KEY"]), 32)

    @patch.object(boot, "audit_runtime_lock")
    @patch.object(boot.subprocess, "run")
    def test_missing_lock_does_not_launch_app(self, run, audit):
        audit.return_value = {"direct_lock_qualified": False}
        result = boot.qualify_django_boot()
        self.assertFalse(result["django_system_check_passed"])
        self.assertFalse(result["release_qualified"])
        run.assert_not_called()

    @patch.object(boot, "audit_runtime_lock")
    @patch.object(boot.subprocess, "run")
    def test_real_check_command_no_migrations_and_release_still_false(self, run, audit):
        audit.return_value = {"direct_lock_qualified": True}
        run.return_value = CompletedProcess([], 0, stdout="System check identified no issues", stderr="")
        result = boot.qualify_django_boot()
        self.assertTrue(result["django_system_check_passed"])
        self.assertFalse(result["release_qualified"])
        args = run.call_args.args[0]
        self.assertEqual(args, [
            sys.executable, "manage.py", "check", "--deploy",
            "--fail-level", "WARNING",
        ])
        self.assertEqual(run.call_args.kwargs["timeout"], 125)
        self.assertNotIn("migrate", args)
        self.assertEqual(run.call_args.kwargs["env"]["DJANGO_SETTINGS_MODULE"],
                         "posthog.settings")
        self.assertEqual(run.call_args.kwargs["env"]["FLIND_READINESS_CHECK"], "1")

    @patch.object(boot, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(boot.subprocess, "run", return_value=CompletedProcess(
        [], 1, stdout="", stderr="ImportError: do-not-print-long-sensitive-strings"
    ))
    def test_failure_reports_only_class_not_exception_body(self, *_):
        result = boot.qualify_django_boot()
        self.assertEqual(result["blocker"], "ImportError")
        self.assertNotIn("do-not-print", str(result))

    @patch.object(boot, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(boot.subprocess, "run", return_value=CompletedProcess(
        [], 0, stdout="", stderr="[error    ] failed to queue task"
    ))
    def test_logged_startup_error_is_not_a_pass(self, *_):
        result = boot.qualify_django_boot()
        self.assertFalse(result["django_system_check_passed"])
        self.assertTrue(result["startup_log_errors"])
        self.assertEqual(result["blocker"], "Startup emitted error-level logs")

    @patch.object(boot, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(boot.subprocess, "run", return_value=CompletedProcess(
        [], 0, stdout="", stderr="?: (security.W003) Missing CSRF"
    ))
    def test_security_warning_is_not_a_pass(self, *_):
        result = boot.qualify_django_boot()
        self.assertFalse(result["django_system_check_passed"])
        self.assertEqual(result["deploy_warning_codes"], ["security.W003"])

    @patch.object(boot, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(boot.subprocess, "run", side_effect=TimeoutExpired("manage.py", 125))
    def test_timeout_fails_closed(self, *_):
        result = boot.qualify_django_boot()
        self.assertFalse(result["django_system_check_passed"])
        self.assertEqual(result["blocker"], "Django system check timed out")


if __name__ == "__main__":
    unittest.main()
