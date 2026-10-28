"""Wave224: real local Git fixture tests of read-only ClickHouse source audit."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.e2e.offline_clickhouse_migration_inventory_wave224 import (
    audit, offline_git_env, git,
)


class Wave224ClickHouseSourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-w224-git-")
        self.root = Path(self.tmp.name)
        self.migrations = self.root / "posthog/clickhouse/migrations"
        self.migrations.mkdir(parents=True)
        self.sql = self.migrations / "sql/0238"
        self.sql.mkdir(parents=True)
        (self.sql / "eu_kafka.sql").write_bytes(b"SELECT 1;\n")
        (self.root / "pyproject.toml").write_text("[project]\nname='flind-test'\n")
        (self.migrations / "0001_initial.py").write_text("operations = []\n")
        (self.migrations / "0002_events.py").write_text("operations = []\n")
        (self.migrations / "0067_copy of migration.py").write_text("operations = []\n")
        (self.migrations / "__init__.py").write_text("")
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Flind Test",
                        "-c", "user.email=flind@example.invalid", "commit", "-qm", "fixture"], check=True)

    def stage_git_symlink(self, relative_path: str, target: str) -> None:
        """Stage a real mode-120000 Git link without requiring OS symlink privileges."""
        blob = subprocess.run(
            ["git", "-C", str(self.root), "hash-object", "-w", "--stdin"],
            input=target.encode("utf-8"), capture_output=True, check=True,
        ).stdout.decode("ascii").strip()
        subprocess.run(
            ["git", "-C", str(self.root), "update-index", "--add",
             "--cacheinfo", "120000", blob, relative_path],
            check=True,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_original_canonical_objects_verified_from_git_not_imported(self):
        result = audit(self.root)
        self.assertTrue(result["source_inventory_qualified"], result)
        self.assertEqual(result["canonical_migration_modules"], 2)
        self.assertEqual(result["noncanonical_module_count"], 1)
        self.assertEqual(result["sql_asset_count"], 1)
        self.assertEqual(result["sql_asset_bytes"], len("SELECT 1;\n"))
        self.assertEqual(result["sql_asset_paths"], ["posthog/clickhouse/migrations/sql/0238/eu_kafka.sql"])
        self.assertIn("0067_copy of migration.py", result["noncanonical_module_paths"][0])
        self.assertFalse(result["clickhouse_schema_qualified"])
        self.assertFalse(result["migrations_applied_qualified"])
        self.assertFalse(result["native_ingestion_e2e_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_digest_is_immutable_git_source_not_modified_worktree(self):
        original = audit(self.root)
        (self.migrations / "0002_events.py").write_text("raise RuntimeError('do not import')\n")
        after = audit(self.root)
        self.assertEqual(original["module_manifest_sha256"], after["module_manifest_sha256"])
        self.assertTrue(after["source_inventory_qualified"])

    def test_historical_noncanonical_commit_changes_manifest(self):
        before = audit(self.root)
        (self.migrations / "0067_copy of migration.py").write_text("operations = [1]\n")
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Flind Test",
                        "-c", "user.email=flind@example.invalid", "commit", "-qm", "history-change"], check=True)
        after = audit(self.root)
        self.assertTrue(before["source_inventory_qualified"])
        self.assertTrue(after["source_inventory_qualified"])
        self.assertNotEqual(before["module_manifest_sha256"], after["module_manifest_sha256"])

    def test_committed_original_sql_change_updates_manifest(self):
        before = audit(self.root)
        (self.sql / "eu_kafka.sql").write_bytes(b"SELECT 2;\n")
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Flind Test",
                        "-c", "user.email=flind@example.invalid", "commit", "-qm", "sql-change"], check=True)
        after = audit(self.root)
        self.assertTrue(before["source_inventory_qualified"])
        self.assertTrue(after["source_inventory_qualified"])
        self.assertNotEqual(before["module_manifest_sha256"], after["module_manifest_sha256"])

    def test_sql_symlink_rejected_without_file_reads(self):
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        self.stage_git_symlink("posthog/clickhouse/migrations/sql/0238/us_mv.sql", "eu_kafka.sql")
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Flind Test",
                        "-c", "user.email=flind@example.invalid", "commit", "-qm", "sql-symlink"], check=True)
        result = audit(self.root)
        self.assertFalse(result["source_inventory_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_unknown_reference_fails_closed(self):
        self.assertFalse(audit(self.root, "--all")["source_inventory_qualified"])
        self.assertFalse(audit(self.root, "refs/heads/../../escape")["source_inventory_qualified"])

    def test_symlink_migration_rejected_without_file_reads(self):
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        self.stage_git_symlink("posthog/clickhouse/migrations/0003_link.py", "0001_initial.py")
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Flind Test",
                        "-c", "user.email=flind@example.invalid", "commit", "-qm", "symlink"], check=True)
        self.assertFalse(audit(self.root)["source_inventory_qualified"])

    def test_no_network_or_mutating_git_commands(self):
        self.assertEqual(offline_git_env()["GIT_NO_LAZY_FETCH"], "1")
        real = subprocess.run
        seen = []

        def observe(*args, **kwargs):
            cmd = args[0]
            if isinstance(cmd, list) and len(cmd) > 3 and cmd[0] == "git":
                seen.append(cmd[3])
                self.assertEqual(kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
                self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            return real(*args, **kwargs)
        with patch(
            "tools.flind.e2e.offline_clickhouse_migration_inventory_wave224.subprocess.run",
            side_effect=observe,
        ):
            self.assertTrue(audit(self.root)["source_inventory_qualified"])
        self.assertEqual(seen, ["rev-parse", "rev-parse", "ls-tree", "cat-file"])

    def test_missing_local_promisor_blob_fails_closed(self):
        real = subprocess.run

        def missing_blob(*args, **kwargs):
            command = args[0]
            if isinstance(command, list) and command[0] == "git" and "--batch-check" in command:
                return subprocess.CompletedProcess(command, 0, stdout=b"deadbeef missing\n", stderr=b"")
            return real(*args, **kwargs)
        with patch(
            "tools.flind.e2e.offline_clickhouse_migration_inventory_wave224.subprocess.run",
            side_effect=missing_blob,
        ):
            result = audit(self.root)
        self.assertFalse(result["source_inventory_qualified"])
        self.assertEqual(result["blocker"], "ValueError")
        self.assertFalse(result["release_qualified"])

    def test_missing_all_canonical_migrations_fails_closed(self):
        (self.migrations / "0001_initial.py").unlink()
        (self.migrations / "0002_events.py").unlink()
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Flind Test",
                        "-c", "user.email=flind@example.invalid", "commit", "-qm", "remove"], check=True)
        result = audit(self.root)
        self.assertFalse(result["source_inventory_qualified"])
        self.assertEqual(result["blocker"], "ValueError")

    def test_missing_noncanonical_history_blob_fails_closed(self):
        real = subprocess.run

        def missing_history_blob(*args, **kwargs):
            command = args[0]
            if isinstance(command, list) and command[0] == "git" and "--batch-check" in command:
                original = real(*args, **kwargs)
                rows = original.stdout.splitlines(keepends=True)
                self.assertEqual(len(rows), 4)
                rows[-2] = rows[-2].split(b" ", 1)[0] + b" missing\n"
                return subprocess.CompletedProcess(command, 0, stdout=b"".join(rows), stderr=b"")
            return real(*args, **kwargs)

        with patch(
            "tools.flind.e2e.offline_clickhouse_migration_inventory_wave224.subprocess.run",
            side_effect=missing_history_blob,
        ):
            receipt = audit(self.root)
        self.assertFalse(receipt["source_inventory_qualified"])
        self.assertFalse(receipt["release_qualified"])

    def test_missing_original_sql_blob_fails_closed(self):
        real = subprocess.run

        def missing_sql_blob(*args, **kwargs):
            command = args[0]
            if isinstance(command, list) and command[0] == "git" and "--batch-check" in command:
                original = real(*args, **kwargs)
                rows = original.stdout.splitlines(keepends=True)
                self.assertEqual(len(rows), 4)
                rows[-1] = rows[-1].split(b" ", 1)[0] + b" missing\n"
                return subprocess.CompletedProcess(command, 0, stdout=b"".join(rows), stderr=b"")
            return real(*args, **kwargs)

        with patch(
            "tools.flind.e2e.offline_clickhouse_migration_inventory_wave224.subprocess.run",
            side_effect=missing_sql_blob,
        ):
            result = audit(self.root)
        self.assertFalse(result["source_inventory_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_git_tree_blob_size_mismatch_fails_closed(self):
        real = subprocess.run

        def wrong_object_size(*args, **kwargs):
            command = args[0]
            if isinstance(command, list) and command[0] == "git" and "--batch-check" in command:
                original = real(*args, **kwargs)
                rows = original.stdout.splitlines(keepends=True)
                parts = rows[0].split(b" ")
                rows[0] = parts[0] + b" blob 999\n"
                return subprocess.CompletedProcess(command, 0, stdout=b"".join(rows), stderr=b"")
            return real(*args, **kwargs)

        with patch(
            "tools.flind.e2e.offline_clickhouse_migration_inventory_wave224.subprocess.run",
            side_effect=wrong_object_size,
        ):
            receipt = audit(self.root)
        self.assertFalse(receipt["source_inventory_qualified"])
        self.assertEqual(receipt["blocker"], "ValueError")

    def test_cli_json_success_and_invalid_ref_exit_codes(self):
        program = Path(__file__).with_name("offline_clickhouse_migration_inventory_wave224.py")
        args = [sys.executable, str(program), "--root", str(self.root), "--ref"]
        success = subprocess.run([*args, "HEAD", "--json"], capture_output=True, text=True, check=False)
        self.assertEqual(success.returncode, 0, success.stderr)
        value = json.loads(success.stdout)
        self.assertTrue(value["source_inventory_qualified"])
        self.assertEqual(value["canonical_migration_modules"], 2)
        self.assertFalse(value["clickhouse_schema_qualified"])
        self.assertFalse(value["release_qualified"])
        denied = subprocess.run(
            [*args, "refs/heads/../../escape", "--json"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(denied.returncode, 2, denied.stderr)
        self.assertFalse(json.loads(denied.stdout)["source_inventory_qualified"])

    def test_git_helper_disallows_write_operations(self):
        with self.assertRaises(ValueError):
            git(self.root, ["checkout", "--", "file"])


if __name__ == "__main__":
    unittest.main()
