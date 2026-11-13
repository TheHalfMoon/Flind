"""Source and fail-closed preflight tests for synthetic two-store migration markers."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/flind/qualify_migration_data_preservation.sh"
WORKFLOW = ROOT / ".github/workflows/flind-runtime-migrations.yml"


class MigrationPreservationWorkflowTests(unittest.TestCase):
    def test_seed_and_verify_straddle_second_migration(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        steps = (
            "First migration run (fresh databases)",
            "Seed synthetic tenant data before migration rerun",
            "Second migration run (idempotency over existing state)",
            "Verify synthetic tenant data survived migration rerun",
            "Verify applied state",
        )
        offsets = [source.index(f"- name: {step}") for step in steps]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn("migration-canary-summary.txt", source)
        self.assertEqual(source.count("bash tools/flind/qualify_migration_data_preservation.sh seed"), 1)
        self.assertEqual(source.count("bash tools/flind/qualify_migration_data_preservation.sh verify"), 1)

    def test_real_negative_controls_follow_positive_parity_and_precede_cleanup(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        steps = (
            'cmp -s "$pg_before" "$pg_after"',
            'cmp -s "$ch_before" "$ch_after"',
            'UPDATE $pg_table SET marker=\'intentionally-tampered\'',
            'Postgres comparator did not detect a modified tenant record',
            'Postgres record did not recover after negative control',
            'TRUNCATE TABLE $ch_table',
            'ClickHouse comparator did not detect a deleted tenant record',
            'ClickHouse records did not recover after negative control',
            'DROP TABLE $pg_table',
            'DROP TABLE $ch_table',
        )
        positions = [source.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("postgres_modified_row_negative_control=pass", source)
        self.assertIn("clickhouse_deleted_row_negative_control=pass", source)
        self.assertIn("post_negative_control_repair_parity=pass", source)

    @unittest.skipUnless(os.name == "posix", "Bash preflight tests require Linux")
    def test_shell_syntax(self) -> None:
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.name == "posix", "Bash preflight tests require Linux")
    def test_preflight_denials_do_not_touch_containers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flind-migration-canary-") as folder:
            tmp = Path(folder)
            marker = tmp / "touched-docker"
            fake = tmp / "docker"
            fake.write_text(
                '#!/bin/sh\nprintf "bad" > "$FLIND_DOCKER_MARKER"\nexit 99\n',
                encoding="utf-8",
            )
            fake.chmod(0o755)
            base = os.environ.copy()
            base.update({
                "GITHUB_ACTIONS": "true",
                "FLIND_SYNTHETIC_MIGRATION_CHECK": "1",
                "DATABASE_URL": "postgres://posthog:posthog@localhost:5432/posthog",
                "CLICKHOUSE_HOST": "localhost",
                "CLICKHOUSE_DATABASE": "posthog",
                "DEBUG": "1",
                "GITHUB_WORKSPACE": str(ROOT),
                "EVIDENCE": str(ROOT / "flind-evidence"),
                "PATH": str(tmp) + os.pathsep + base.get("PATH", ""),
                "FLIND_DOCKER_MARKER": str(marker),
            })
            cases = [
                ({"GITHUB_ACTIONS": "false"}, "ephemeral GitHub runner"),
                ({"FLIND_SYNTHETIC_MIGRATION_CHECK": "0"}, "explicit synthetic opt-in"),
                ({"DATABASE_URL": "postgres://production:5432/users"}, "unexpected Postgres URL"),
                ({"CLICKHOUSE_HOST": "production.example"}, "unexpected ClickHouse target"),
                ({"CLICKHOUSE_DATABASE": "customers"}, "unexpected ClickHouse target"),
                ({"DEBUG": "0"}, "dev-only context"),
                ({"EVIDENCE": str(tmp / "foreign")}, "unexpected evidence location"),
            ]
            for mode in ("seed", "verify"):
                for overrides, error in cases:
                    with self.subTest(mode=mode, overrides=overrides):
                        env = dict(base)
                        env.update(overrides)
                        result = subprocess.run(
                            ["bash", str(SCRIPT), mode], cwd=ROOT, env=env,
                            capture_output=True, text=True,
                        )
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn(error, result.stderr)
                        self.assertFalse(marker.exists(), "An unsafe preflight reached Docker")
            missing_mode = subprocess.run(
                ["bash", str(SCRIPT)], cwd=ROOT, env=base, capture_output=True, text=True,
            )
            self.assertEqual(missing_mode.returncode, 2)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
