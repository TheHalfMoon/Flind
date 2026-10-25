"""Sanitized diagnostic labels for bounded real Django migrations (Wave 63)."""
import io
import unittest
from unittest.mock import MagicMock, patch

from tools.flind import qualify_isolated_migrations_wave55 as probe
from tools.flind import qualify_resumable_migrations_wave57 as resume


class MigrationDiagnosticWave63Tests(unittest.TestCase):
    def test_last_stalled_migration_is_reported_without_arbitrary_logs(self):
        output = (
            "DEBUG provider token=super-private\n"
            "Operations to perform:\n"
            "  Applying contenttypes.0001_initial... OK\n"
            "  Applying posthog.0245_create_flag... OK\n"
            "  Applying actions.0002_alter_action_created_by..."
        )
        progress = probe.migration_console_progress(output)
        self.assertEqual(progress["last_attempted_migration"],
                         "actions.0002_alter_action_created_by")
        self.assertEqual(progress["last_console_completed_migration"],
                         "posthog.0245_create_flag")
        self.assertEqual(progress["interrupted_migration"],
                         "actions.0002_alter_action_created_by")
        self.assertNotIn("super-private", str(progress))
        self.assertNotIn("provider token", str(progress))

    def test_clean_completed_output_does_not_report_interruption(self):
        progress = probe.migration_console_progress(
            "  Applying auth.0012_alter_user_first_name_max_length... OK\n"
        )
        self.assertEqual(progress["last_attempted_migration"],
                         "auth.0012_alter_user_first_name_max_length")
        self.assertIsNone(progress["interrupted_migration"])

    def test_unrecognized_lines_never_echo_secrets_or_sql(self):
        outputs = (
            "",
            "Traceback: DATABASE_URL=postgres://user:secret@127.0.0.1/x",
            "  Applying invalid.name;DROP TABLE accounts... OK\n",
            "  Applying foo.verylongname" + "x" * 400 + "... OK\n",
            "  Applying auth.0012... OK secret=leak\n",
        )
        for output in outputs:
            with self.subTest(sample=output[:32]):
                receipt = probe.migration_console_progress(output)
                self.assertTrue(
                    all(value is None for value in receipt.values()),
                    receipt,
                )

    @patch.object(probe, "read_applied_count", return_value=0)
    @patch.object(probe.subprocess, "Popen")
    @patch.object(probe.tempfile, "TemporaryFile")
    def test_django_startup_failure_is_classified_without_raw_output(self, log, popen, _count):
        proc = MagicMock()
        proc.poll.return_value = 2
        proc.returncode = 2
        popen.return_value = proc
        log.return_value = io.StringIO(
            "Error loading Django: token=local-password\n"
            "RuntimeError: local-password must remain private\n"
        )
        result = probe.attempt_migrations(16444, "private-password", "flind_ephemeral")
        self.assertFalse(result["isolated_migrations_completed"])
        self.assertTrue(result["django_console_output_seen"])
        self.assertFalse(result["django_migration_stage_seen"])
        self.assertEqual(result["django_error_class"], "RuntimeError")
        self.assertIsNone(result["last_attempted_migration"])
        self.assertNotIn("local-password", str(result))
        self.assertNotIn("private-password", str(result))
        self.assertIn("-u", popen.call_args.args[0])
        self.assertIn("1", popen.call_args.args[0])

    @patch.object(probe, "read_applied_count", return_value=0)
    @patch.object(probe.subprocess, "Popen")
    @patch.object(probe.tempfile, "TemporaryFile")
    def test_migrate_stage_progress_is_visible_when_row_count_zero(self, log, popen, _count):
        proc = MagicMock()
        proc.poll.return_value = 2
        proc.returncode = 2
        popen.return_value = proc
        log.return_value = io.StringIO(
            "Operations to perform:\n"
            "Running migrations:\n"
            "  Applying posthog.0001_initial...\n"
        )
        result = probe.attempt_migrations(16444, "local", "flind_ephemeral")
        self.assertTrue(result["django_migration_stage_seen"])
        self.assertEqual(result["interrupted_migration"], "posthog.0001_initial")
        self.assertFalse(result["isolated_migrations_completed"])

    def test_resume_forwards_sanitized_attempted_label(self):
        with patch.object(resume, "attempt_migrations") as migrations:
            migrations.return_value = {
                "isolated_migrations_completed": False,
                "migration_rows_applied_to_disposable_db": 245,
                "blocker": "Migration time limit reached",
                "last_committed_migration": "auth.0012_something",
                "last_attempted_migration": "actions.0002_alter",
                "interrupted_migration": "actions.0002_alter",
            }
            result = resume.run_resumable(
                16444, "local-secret", "flind_ephemeral",
                max_rounds=1, seconds_per_round=20,
            )
            self.assertFalse(result["full_schema_migrations_completed"])
            self.assertEqual(result["migration_progress"][0]["interrupted_migration"],
                             "actions.0002_alter")
            self.assertFalse(result["release_qualified"])
            self.assertNotIn("local-secret", str(result))


if __name__ == "__main__":
    unittest.main()
