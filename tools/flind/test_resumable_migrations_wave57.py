"""Migration retries retain progress in one private database; always NO-GO for release."""
import unittest
from unittest.mock import patch

from tools.flind import qualify_resumable_migrations_wave57 as run


class ResumableMigrationsWave57Tests(unittest.TestCase):
    @patch.object(run, "attempt_migrations")
    def test_timeboxed_retry_resumes_on_same_database(self, migrate):
        migrate.side_effect = [
            {
                "isolated_migrations_completed": False,
                "migration_rows_applied_to_disposable_db": 130,
                "last_committed_migration": "posthog.0050_initial",
                "blocker": "Migration time limit reached",
            },
            {
                "isolated_migrations_completed": True,
                "migration_rows_applied_to_disposable_db": 160,
                "last_committed_migration": "posthog.0060_final",
            },
        ]
        report = run.run_resumable(16111, "secret", "flind_ephemeral", max_rounds=2)
        self.assertTrue(report["full_schema_migrations_completed"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual([step["newly_committed_rows"] for step in report["migration_progress"]], [130, 30])
        self.assertEqual(report["rounds_executed"], 2)
        for call in migrate.call_args_list:
            self.assertEqual(call.args, (16111, "secret", "flind_ephemeral"))

    @patch.object(run, "attempt_migrations")
    def test_zero_new_progress_stops_without_third_attempt(self, migrate):
        migrate.side_effect = [
            {"migration_rows_applied_to_disposable_db": 120, "blocker": "Migration time limit reached"},
            {"migration_rows_applied_to_disposable_db": 120, "blocker": "Migration time limit reached"},
        ]
        report = run.run_resumable(16111, "private", "flind_ephemeral", max_rounds=3)
        self.assertFalse(report["full_schema_migrations_completed"])
        self.assertEqual(report["rounds_executed"], 2)
        self.assertEqual(report["blocker"], "No new committed migration progress")
        self.assertEqual(migrate.call_count, 2)

    @patch.object(run, "attempt_migrations")
    def test_decreasing_row_count_is_not_a_pass(self, migrate):
        migrate.side_effect = [
            {"migration_rows_applied_to_disposable_db": 10, "blocker": "Migration time limit reached"},
            {"migration_rows_applied_to_disposable_db": 9, "isolated_migrations_completed": True},
        ]
        report = run.run_resumable(16111, "private", "flind_ephemeral", max_rounds=2)
        self.assertFalse(report["full_schema_migrations_completed"])
        self.assertEqual(report["blocker"], "Migration receipt count invalid or regressed")

    @patch.object(run, "attempt_migrations")
    def test_first_round_error_never_retries_without_time_guard(self, migrate):
        migrate.return_value = {
            "migration_rows_applied_to_disposable_db": 22,
            "blocker": "Database extension unavailable",
        }
        report = run.run_resumable(16111, "private", "flind_ephemeral", max_rounds=3)
        self.assertFalse(report["full_schema_migrations_completed"])
        self.assertEqual(report["rounds_executed"], 1)
        migrate.assert_called_once()

    @patch.object(run, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": False})
    @patch.object(run, "isolated_postgres")
    def test_missing_lock_never_creates_any_cluster(self, pg, _lock):
        report = run.qualify_resumable()
        self.assertFalse(report["full_schema_migrations_completed"])
        pg.assert_not_called()

    @patch.object(run, "audit_runtime_lock",
                  return_value={"direct_lock_qualified": True})
    @patch.object(run, "isolated_postgres")
    def test_successful_migrations_still_do_not_qualify_release(self, pg, _lock):
        pg.return_value = {
            "postgres_component_passed": True,
            "django_migration_plan": {
                "full_schema_migrations_completed": True,
                "rounds_executed": 2,
                "migration_committed_rows_total": 777,
                "migration_progress": [],
                "release_qualified": False,
            },
        }
        report = run.qualify_resumable(rounds=2)
        self.assertTrue(report["full_schema_migrations_completed"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual(report["migration_committed_rows_total"], 777)

    def test_unbounded_options_refused(self):
        for rounds, seconds in [(0, 100), (4, 100), (2, 19), (2, 121)]:
            with self.subTest(rounds=rounds, seconds=seconds):
                with self.assertRaises(ValueError):
                    run.qualify_resumable(rounds, seconds)


if __name__ == "__main__":
    unittest.main()
