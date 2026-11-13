"""Fail-closed guard tests for the runner-local synthetic PostgreSQL restore."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/flind/qualify_postgres_backup_restore_synthetic.sh"
EXPECTED_URL = "postgres://posthog:posthog@localhost:5432/posthog"


@unittest.skipUnless(os.name == "posix", "Bash guard is executed by Linux CI")
class SyntheticRestoreGuardTests(unittest.TestCase):
    def test_bash_syntax(self) -> None:
        result = subprocess.run(["bash", "-n", str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_preflight_rejects_unsafe_context_before_docker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flind-pg-guard-") as temp:
            tmp = Path(temp)
            marker = tmp / "docker-called"
            fake_docker = tmp / "docker"
            fake_docker.write_text(
                '#!/bin/sh\nprintf "unexpected docker access" > "$FLIND_DOCKER_MARKER"\nexit 99\n',
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            base = os.environ.copy()
            base.update({
                "PATH": str(tmp) + os.pathsep + base.get("PATH", ""),
                "GITHUB_ACTIONS": "true",
                "FLIND_SYNTHETIC_PG_RESTORE": "1",
                "DATABASE_URL": EXPECTED_URL,
                "DEBUG": "1",
                "GITHUB_WORKSPACE": str(ROOT),
                "EVIDENCE": str(ROOT / "flind-evidence"),
                "RUNNER_TEMP": str(tmp),
                "FLIND_DOCKER_MARKER": str(marker),
            })
            cases = (
                ("GITHUB_ACTIONS", "false", "GitHub Actions ephemeral runner"),
                ("FLIND_SYNTHETIC_PG_RESTORE", "0", "explicit synthetic opt-in"),
                ("DATABASE_URL", "postgres://other:pass@remote:5432/prod", "unexpected database URL"),
                ("DEBUG", "0", "development testing context"),
                ("EVIDENCE", str(tmp / "foreign"), "unexpected evidence destination"),
                ("GITHUB_WORKSPACE", str(tmp), "unexpected evidence destination"),
            )
            for key, value, fragment in cases:
                with self.subTest(field=key):
                    env = dict(base)
                    env[key] = value
                    result = subprocess.run(["bash", str(SCRIPT)], cwd=ROOT, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(fragment, result.stderr)
                    self.assertFalse(marker.exists(), f"Unsafe case {key} touched Docker")


if __name__ == "__main__":
    unittest.main()
