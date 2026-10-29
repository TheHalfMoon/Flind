"""Wave259: fail-closed tests for owner-only Keeper + CH migration tracking."""

from __future__ import annotations

from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from tools.flind import qualify_infi_synthetic_migration_wave260 as q

ORIGINAL = Path(q.__file__)


class Wave260InfiSyntheticMigrationTests(unittest.TestCase):
    def test_release_and_full_migrations_always_remain_unqualified(self):
        self.assertIs(q.REPORT["release_qualified"], False)
        self.assertIs(q.REPORT["full_original_migrations_executed"], False)
        self.assertIs(q.REPORT["infi_migration_runner_executed"], False)
        self.assertIs(q.REPORT["multinode_replication_qualified"], False)

    def test_sql_refuses_unsafe_ports_and_overlong_payloads_before_connection(self):
        with patch.object(q, "HTTPConnection") as transport:
            for port, statement in [
                (True, "SELECT 1"), (0, "SELECT 1"), (65536, "SELECT 1"),
                (18000, "SELECT 'é'"), (18000, "X" * 2001),
            ]:
                with self.subTest(port=port):
                    with self.assertRaises(ValueError):
                        q.http_sql(port, statement)
            transport.assert_not_called()

    def test_sql_always_posts_to_private_loopback_only(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"1\n"
        with patch.object(q, "HTTPConnection") as transport:
            transport.return_value.getresponse.return_value = response
            got = q.http_sql(12345, "SELECT 1")
        self.assertEqual(got, "1")
        transport.assert_called_once_with("127.0.0.1", 12345, timeout=11)
        transport.return_value.request.assert_called_once_with(
            "POST", "/?wait_end_of_query=1", b"SELECT 1",
            headers={"Content-Type": "text/plain"},
        )

    def test_sql_non200_refuses_without_sql_result_promotion(self):
        response = MagicMock()
        response.status = 500
        response.read.return_value = b"synthetic SQL failure"
        with patch.object(q, "HTTPConnection") as transport:
            transport.return_value.getresponse.return_value = response
            with self.assertRaisesRegex(RuntimeError, "clickhouse_ddl_http_500"):
                q.http_sql(12345, "SELECT 1")

    def test_keeper_health_is_loopback_and_requires_imok(self):
        sock = MagicMock()
        sock.__enter__.return_value = sock
        sock.recv.return_value = b"imok"
        with patch.object(q.socket, "create_connection", return_value=sock) as connect:
            self.assertTrue(q.keeper_ready(12345))
        connect.assert_called_once_with(("127.0.0.1", 12345), timeout=1)
        sock.sendall.assert_called_once_with(b"ruok")

    def test_keeper_refuses_nonready_result(self):
        sock = MagicMock()
        sock.__enter__.return_value = sock
        sock.recv.return_value = b"ruok"
        with patch.object(q.socket, "create_connection", return_value=sock):
            self.assertFalse(q.keeper_ready(12345))

    def test_insufficient_disk_prevents_any_service_or_scratch_creation(self):
        with TemporaryDirectory(prefix="flind-wave259-unit-") as tmp:
            root = Path(tmp)
            source = root / "migrate_clickhouse.py"
            source.write_text("synthetic migration runner fixture")
            scratch = root / "not-created"
            with patch.object(q, "ROOT", root), patch.object(q, "SCRATCH", scratch), patch.object(
                q, "CHECKOUT", root
            ), patch.object(q, "ORIGINAL", source), patch.object(
                q.subprocess, "check_output", return_value=q.REPORT["source_git_sha"] + "\n"
            ), patch.object(q, "free_space", return_value=18 * 1024**3), patch.object(
                q, "start"
            ) as start:
                with self.assertRaisesRegex(RuntimeError, "insufficient_19GiB_preflight"):
                    q.run()
                start.assert_not_called()
            self.assertFalse(scratch.exists())

    def test_wrong_source_checkout_refused_before_service_creation(self):
        with TemporaryDirectory(prefix="flind-wave259-unit-") as tmp:
            root = Path(tmp)
            source = root / "migrate_clickhouse.py"
            source.write_text("synthetic migration runner fixture")
            scratch = root / "not-created"
            with patch.object(q, "ROOT", root), patch.object(q, "SCRATCH", scratch), patch.object(
                q, "CHECKOUT", root
            ), patch.object(q, "ORIGINAL", source), patch.object(
                q, "free_space", return_value=21 * 1024**3
            ), patch.object(
                q.subprocess, "check_output", return_value=b"unexpected-source-commit\n"
            ), patch.object(q, "start") as start:
                with self.assertRaisesRegex(RuntimeError, "unexpected_source_commit"):
                    q.run()
                start.assert_not_called()
            self.assertFalse(scratch.exists())

    def test_no_source_optimized_away_assert_guards(self):
        import ast
        tree = ast.parse(ORIGINAL.read_text())
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))

    def test_actual_tracking_ddl_source_immutability(self):
        import subprocess
        source = q.ORIGINAL
        if not source.is_file() or not q.CHECKOUT.is_dir():
            self.skipTest("owner-only source checkout is unavailable")
        local = subprocess.check_output(
            ["git", "-C", str(q.CHECKOUT), "hash-object", str(source)],
            text=True,
        ).strip()
        self.assertEqual(local, "aa993e44eb204f118392a1e0a483fcfa2e201566")
        text = source.read_text()
        self.assertIn("ENGINE = ReplicatedMergeTree(", text)
        self.assertIn("ENGINE = Distributed({cluster}", text)
        self.assertIn("CREATE DATABASE IF NOT EXISTS {database} ON CLUSTER {cluster}", text)


    def test_exact_one_synthetic_package_only(self):
        code = ORIGINAL.read_text()
        self.assertIn("pkgname='flind_wave260_synthetic_one_migration'", code)
        self.assertIn("database.migrate(pkgname,up_to=1,replicated=True)", code)
        self.assertEqual(code.count("database.migrate(pkgname,up_to=1,replicated=True)"), 2)
        self.assertIn("original_flind_django_migrate_command_executed", code)
        self.assertFalse(q.REPORT["full_original_migrations_executed"])

    def test_locked_infi_git_commit_is_required(self):
        code = ORIGINAL.read_text()
        self.assertIn("4e3996becf66bf5c26580aff12a80425d9d56fe5",code)
        self.assertIn("infi_clickhouse_orm_git_commit_mismatch",code)
        self.assertIn("infi_clickhouse_orm_lock_version_drift",code)
        self.assertIn("real_infi_migration_repeat_noop",code)
        self.assertFalse(q.REPORT["release_qualified"])


if __name__ == "__main__":
    unittest.main()
