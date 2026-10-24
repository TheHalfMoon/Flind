"""Check hermetic Postgres lifecycle and safe SQL probe without touching DBs."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import unittest

from tools.flind import qualify_ephemeral_postgres as pg


class EphemeralPostgresWave54Tests(unittest.TestCase):
    def test_real_binary_discovery_is_under_postgresql17_only(self):
        for name in pg.pg_commands():
            self.assertIn(name, ("initdb", "pg_ctl", "createdb", "psql"))
            self.assertTrue(pg.pg_commands()[name].startswith(str(pg.DEFAULT_PG_BIN_DIR)))

    def test_port_is_loopback_ephemeral(self):
        port = pg.choose_loopback_port()
        self.assertGreater(port, 0)
        self.assertLess(port, 65536)

    @patch.object(pg, "choose_loopback_port", return_value=16379)
    @patch.object(pg, "execute")
    def test_success_uses_owned_scram_cluster_and_stops(self, execute, _port):
        def fake_result(argv, **kwargs):
            if argv[0].endswith("/psql") and "SHOW server_version" in argv:
                return __import__("subprocess").CompletedProcess(argv, 0, "17.9\n", "")
            if argv[0].endswith("/psql"):
                return __import__("subprocess").CompletedProcess(
                    argv, 0, "BEGIN\nCREATE TABLE\nINSERT 0 3\n3|14\nROLLBACK\n", ""
                )
            return __import__("subprocess").CompletedProcess(argv, 0, "", "")
        execute.side_effect = fake_result
        report = pg.isolated_postgres()
        self.assertTrue(report["postgres_component_passed"])
        self.assertFalse(report["migration_qualified"])
        self.assertFalse(report["release_qualified"])
        calls = [call.args[0] for call in execute.call_args_list]
        init, start, show, createdb, sql, stop = calls
        self.assertIn("--auth", init)
        self.assertIn("scram-sha-256", init)
        self.assertIn("--pwfile", init)
        self.assertIn("listen_addresses=127.0.0.1", " ".join(start))
        self.assertIn("port=16379", " ".join(start))
        self.assertIn("CREATE TEMP TABLE", " ".join(sql))
        self.assertIn("ROLLBACK", " ".join(sql))
        self.assertIn("stop", stop)
        self.assertNotIn("migrate", " ".join(" ".join(args) for args in calls))
        for call in execute.call_args_list:
            self.assertTrue(call.kwargs["env"].get("PGPASSWORD"))
            self.assertIn("flind-postgresql-", call.kwargs["env"]["HOME"])

    @patch.object(pg, "choose_loopback_port", return_value=16379)
    @patch.object(pg, "execute")
    def test_failed_readback_still_stops_isolated_cluster(self, execute, _port):
        def fake_result(argv, **kwargs):
            if argv[0].endswith("/psql") and "SHOW server_version" in argv:
                return __import__("subprocess").CompletedProcess(argv, 0, "17.9\n", "")
            if argv[0].endswith("/psql"):
                return __import__("subprocess").CompletedProcess(argv, 0, "2|0\n", "")
            return __import__("subprocess").CompletedProcess(argv, 0, "", "")
        execute.side_effect = fake_result
        result = pg.isolated_postgres()
        self.assertFalse(result["postgres_component_passed"])
        self.assertEqual(execute.call_args_list[-1].args[0][-1], "stop")

    @patch.object(pg, "pg_commands", side_effect=FileNotFoundError())
    def test_missing_toolchain_fails_closed(self, _commands):
        result = pg.isolated_postgres()
        self.assertFalse(result["postgres_component_passed"])
        self.assertFalse(result["release_qualified"])

    def test_unknown_postgres_directory_cannot_trigger_fallback(self):
        with TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                pg.pg_commands(Path(root))


if __name__ == "__main__":
    unittest.main()
