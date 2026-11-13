"""Fail-closed source-only tests for ephemeral ClickHouse Native export/import."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/flind/qualify_clickhouse_native_recovery.sh"
WORKFLOW = ROOT / ".github/workflows/flind-runtime-migrations.yml"


class ClickHouseNativeRecoveryGuards(unittest.TestCase):
    def test_workflow_is_explicit_opt_in_after_migrations(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("clickhouse_recovery:", source)
        self.assertIn("default: false", source)
        name = "- name: Verify synthetic ClickHouse Native export/import and negative control"
        position = source.index(name)
        self.assertLess(source.index("- name: Verify applied state"), position)
        self.assertIn("inputs.clickhouse_recovery == true", source[position:position + 290])
        self.assertIn("clickhouse-native-recovery.txt", source)
        self.assertNotIn("upload-artifact@", source)

    @unittest.skipUnless(os.name == "posix", "Bash syntax requires POSIX")
    def test_shell_syntax(self) -> None:
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.name == "posix", "Bash executable guard requires POSIX")
    def test_dangerous_environment_never_reaches_docker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flind-ch-native-") as folder:
            tmp = Path(folder)
            marker = tmp / "docker-called"
            docker = tmp / "docker"
            docker.write_text(
                '#!/bin/sh\nprintf "unexpected container call" > "$FLIND_DOCKER_MARKER"\nexit 99\n',
                encoding="utf-8",
            )
            docker.chmod(0o755)
            base = dict(os.environ)
            base.update({
                "GITHUB_ACTIONS": "true",
                "FLIND_SYNTHETIC_CLICKHOUSE_RECOVERY": "1",
                "CLICKHOUSE_HOST": "localhost",
                "CLICKHOUSE_DATABASE": "posthog",
                "DATABASE_URL": "postgres://posthog:posthog@localhost:5432/posthog",
                "DEBUG": "1",
                "GITHUB_WORKSPACE": str(ROOT),
                "EVIDENCE": str(ROOT / "flind-evidence"),
                "RUNNER_TEMP": str(tmp),
                "FLIND_DOCKER_MARKER": str(marker),
                "PATH": str(tmp) + os.pathsep + base.get("PATH", ""),
            })
            cases = (
                ("GITHUB_ACTIONS", "false", "ephemeral GitHub runner"),
                ("FLIND_SYNTHETIC_CLICKHOUSE_RECOVERY", "0", "explicit synthetic opt-in"),
                ("CLICKHOUSE_HOST", "prod.example", "unexpected ClickHouse target"),
                ("CLICKHOUSE_DATABASE", "production", "unexpected ClickHouse target"),
                ("DATABASE_URL", "postgres://prod.internal/real", "unexpected companion Postgres URL"),
                ("DEBUG", "0", "development testing context"),
                ("EVIDENCE", str(tmp / "foreign"), "unexpected evidence location"),
                ("RUNNER_TEMP", str(tmp / "missing"), "ephemeral temp required"),
                ("GITHUB_WORKSPACE", str(tmp), "unexpected evidence location"),
            )
            for key, value, message in cases:
                with self.subTest(field=key):
                    env = dict(base)
                    env[key] = value
                    result = subprocess.run(
                        ["bash", str(SCRIPT)], cwd=ROOT, env=env,
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertFalse(marker.exists(), "Unsafe preflight reached Docker")


if __name__ == "__main__":
    unittest.main()
