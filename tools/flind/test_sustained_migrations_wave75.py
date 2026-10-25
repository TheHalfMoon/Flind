"""Wave 75 guardrails for real bounded sustained Django migrations."""
from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

from tools.flind import qualify_sustained_migrations_wave75 as q


def attempt(*, count, done=False, blocker="Migration time limit reached", stage=True):
    return {
        "migration_rows_applied_to_disposable_db": count,
        "isolated_migrations_completed": done,
        "blocker": blocker,
        "django_migration_stage_seen": stage,
        "last_committed_migration": "posthog.0001_initial",
        "last_attempted_migration": "posthog.0002_next",
        "django_error_class": None,
    }


class SustainedMigrationsWave75(unittest.TestCase):
    def test_bounds_are_exact_and_bool_is_not_an_int(self):
        for rounds, seconds in (
            (0, 120), (4, 120), (2, 0), (1, 59), (2, 361),
            (True, 120), (1, True), (1.5, 90),
        ):
            with self.subTest(rounds=rounds, seconds=seconds):
                self.assertFalse(q.admitted(rounds, seconds))
        self.assertTrue(q.admitted(1, 360))
        self.assertTrue(q.admitted(3, 360))

    @patch.object(q, "attempt_migrations")
    def test_exact_original_command_api_and_resumable_commits(self, migration):
        migration.side_effect = [
            attempt(count=2400),
            attempt(count=2700),
            attempt(count=3200, done=True),
        ]
        report = q.run_sustained(5421, "synthetic-password", "temp", rounds=3, seconds=360)
        self.assertTrue(report["full_schema_migrations_completed"])
        self.assertEqual(report["rounds_executed"], 3)
        self.assertEqual(report["committed_migration_rows"], 3200)
        self.assertEqual([r["new_rows"] for r in report["round_progress"]], [2400, 300, 500])
        self.assertFalse(report["release_qualified"])
        self.assertEqual(migration.call_count, 3)
        for call in migration.call_args_list:
            self.assertEqual(call.args, (5421, "synthetic-password", "temp"))
            self.assertEqual(call.kwargs, {"max_seconds": 360})
        self.assertNotIn("synthetic-password", str(report))

    @patch.object(q, "attempt_migrations")
    def test_zero_applied_migrations_cannot_qualify_even_on_exit_zero(self, migration):
        migration.return_value = attempt(count=0, done=True)
        receipt = q.run_sustained(5432, "secret", "temp", rounds=2, seconds=360)
        self.assertFalse(receipt["full_schema_migrations_completed"])
        migration.assert_called_once()

    @patch.object(q, "attempt_migrations")
    def test_timeout_with_forward_progress_remains_unqualified(self, migration):
        migration.side_effect = [attempt(count=2300), attempt(count=2510)]
        result = q.run_sustained(5421, "secret", "temp", rounds=2, seconds=240)
        self.assertFalse(result["full_schema_migrations_completed"])
        self.assertEqual(result["rounds_executed"], 2)
        self.assertEqual(result["blocker"], "Bounded sustained migration rounds exhausted")

    @patch.object(q, "attempt_migrations")
    def test_zero_committed_rows_stops_without_repeated_restarts(self, migration):
        migration.return_value = attempt(count=0, stage=False)
        result = q.run_sustained(5421, "secret", "temp", rounds=3, seconds=360)
        self.assertEqual(result["rounds_executed"], 1)
        self.assertIn("startup", result["blocker"])
        migration.assert_called_once()

    @patch.object(q, "attempt_migrations")
    def test_failed_migration_does_not_retry_away_real_error(self, migration):
        migration.return_value = attempt(count=2000, blocker="IntegrityError")
        result = q.run_sustained(5421, "secret", "temp", rounds=3, seconds=360)
        self.assertFalse(result["full_schema_migrations_completed"])
        self.assertEqual(result["rounds_executed"], 1)
        self.assertEqual(result["blocker"], "Migration command failed before time bound")
        migration.assert_called_once()

    @patch.object(q, "attempt_migrations")
    def test_recognized_django_error_is_never_retried_even_if_timed_out(self, migration):
        payload = attempt(count=2400)
        payload["django_error_class"] = "IntegrityError"
        migration.return_value = payload
        receipt = q.run_sustained(5432, "private", "temp", rounds=3, seconds=360)
        self.assertFalse(receipt["full_schema_migrations_completed"])
        self.assertIn("error", receipt["blocker"].lower())
        migration.assert_called_once()

    @patch.object(q, "attempt_migrations")
    def test_regressed_count_is_not_accepted(self, migration):
        migration.side_effect = [attempt(count=3000), attempt(count=2000)]
        result = q.run_sustained(5421, "secret", "temp", rounds=3, seconds=360)
        self.assertFalse(result["full_schema_migrations_completed"])
        self.assertIn("regressed", result["blocker"])
        self.assertEqual(result["committed_migration_rows"], 3000)

    @patch.object(q, "attempt_migrations")
    def test_boolean_or_missing_count_is_not_a_success(self, migration):
        for value in (True, None, "10", -1):
            with self.subTest(value=value):
                migration.return_value = attempt(count=value, done=True)
                result = q.run_sustained(5421, "secret", "temp", rounds=3, seconds=360)
                self.assertFalse(result["full_schema_migrations_completed"])

    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock")
    @patch.object(q.shutil, "disk_usage")
    def test_low_disk_refused_before_lock_or_postgres(self, disk, locked, postgres):
        disk.return_value = type("Disk", (), {"free": 5 * 1024 ** 3})()
        report = q.qualify_sustained(rounds=2, seconds=360)
        self.assertFalse(report["full_schema_migrations_completed"])
        postgres.assert_not_called()
        locked.assert_not_called()

    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": False})
    @patch.object(q.shutil, "disk_usage")
    def test_wrong_python_refused_before_cluster(self, disk, _locked, postgres):
        disk.return_value = type("Disk", (), {"free": 14 * 1024 ** 3})()
        report = q.qualify_sustained()
        self.assertFalse(report["full_schema_migrations_completed"])
        postgres.assert_not_called()

    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(q.shutil, "disk_usage")
    def test_fake_claim_from_failed_cluster_is_rejected(self, disk, _locked, postgres):
        disk.return_value = type("Disk", (), {"free": 15 * 1024 ** 3})()
        postgres.return_value = {
            "postgres_component_passed": False,
            "django_migration_plan": {
                "full_schema_migrations_completed": True,
            },
        }
        report = q.qualify_sustained()
        self.assertFalse(report["full_schema_migrations_completed"])

    @patch.object(q, "qualify_sustained", return_value={
        "full_schema_migrations_completed": False,
        "release_qualified": False,
        "blocker": "Not finished",
    })
    def test_failure_receipt_json_and_nonzero_exit(self, _qualified):
        with redirect_stdout(StringIO()) as output:
            code = q.main(["--json", "--rounds", "1", "--seconds", "360"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())["release_qualified"])

    @patch.object(q, "isolated_postgres")
    @patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": True})
    @patch.object(q.shutil, "disk_usage")
    def test_callback_keeps_same_database_for_rounds(self, disk, _locked, postgres):
        disk.return_value = type("Disk", (), {"free": 15 * 1024 ** 3})()
        with patch.object(q, "run_sustained", return_value={
            "full_schema_migrations_completed": True,
            "rounds_executed": 2, "committed_migration_rows": 3311,
        }) as runs:
            postgres.side_effect = lambda *, on_ready: {
                "postgres_component_passed": True,
                "django_migration_plan": on_ready(5432, "secret", "one-private-db"),
            }
            out = q.qualify_sustained(rounds=2, seconds=300)
        self.assertTrue(out["full_schema_migrations_completed"])
        self.assertFalse(out["release_qualified"])
        runs.assert_called_once_with(5432, "secret", "one-private-db", rounds=2, seconds=300)


if __name__ == "__main__":
    unittest.main()
