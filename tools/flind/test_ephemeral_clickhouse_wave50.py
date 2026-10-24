"""Test ClickHouse isolated HTTP and process lifecycle without needing a server."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree

from tools.flind import qualify_ephemeral_clickhouse as ch


class FakeHTTPResponse:
    def __init__(self, status=200, value=b"1\n"):
        self.status = status
        self.value = value

    def read(self, limit):
        return self.value[:limit]


class EphemeralClickhouseWave50Tests(unittest.TestCase):
    def test_isolated_config_restricts_host_and_paths_and_memory(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            config = ch.write_isolated_config(root, 18000)
            xml = ElementTree.parse(config).getroot()
            self.assertEqual(xml.findtext("listen_host"), "127.0.0.1")
            self.assertEqual(xml.findtext("http_port"), "18000")
            self.assertEqual(xml.findtext("max_server_memory_usage"), "536870912")
            self.assertEqual(xml.findtext("background_pool_size"), "16")
            self.assertTrue(xml.findtext("path").startswith(temp))
            self.assertTrue(xml.findtext("users_config").startswith(temp))
            user_xml = ElementTree.parse(root / "users.xml").getroot()
            self.assertEqual(user_xml.findtext("./users/default/networks/ip"), "127.0.0.1")
            self.assertFalse((root / "data").joinpath("flind_probe").exists())

    @patch.object(ch, "HTTPConnection")
    def test_http_client_never_uses_remote_host_or_follows_redirects(self, connection):
        client = MagicMock()
        client.getresponse.return_value = FakeHTTPResponse(status=302, value=b"redirect")
        connection.return_value = client
        with self.assertRaises(ValueError):
            ch.sql_http(18123, "SELECT 1")
        self.assertEqual(connection.call_args.args, ("127.0.0.1", 18123))
        self.assertEqual(client.request.call_args.args[:2], ("POST", "/"))
        client.close.assert_called_once()

    @patch.object(ch, "HTTPConnection")
    def test_sql_http_requires_exact_success(self, connection):
        client = MagicMock()
        client.getresponse.return_value = FakeHTTPResponse(status=200, value=b"3\t60\n")
        connection.return_value = client
        self.assertEqual(ch.sql_http(18123, "SELECT 1"), b"3\t60\n")
        with self.assertRaises(ValueError):
            ch.sql_http(18123, "x" * 257)

    @patch.object(ch, "sql_http")
    def test_roundtrip_creates_inserts_reads_and_drops_table(self, sql):
        sql.side_effect = [b"1\n", b"", b"", b"3\t60\n", b""]
        receipt = ch.query_roundtrip(18123)
        self.assertEqual(receipt, {"rows": 3, "sum": 60})
        commands = [x.args[1] for x in sql.call_args_list]
        self.assertIn("ENGINE = Memory", commands[1])
        self.assertIn("(10),(20),(30)", commands[2])
        self.assertIn("DROP TABLE IF EXISTS", commands[-1])

    @patch.object(ch, "sql_http")
    def test_roundtrip_mismatch_drops_temporary_table(self, sql):
        sql.side_effect = [b"1\n", b"", b"", b"2\t30\n", b""]
        with self.assertRaisesRegex(ValueError, "read-back mismatch"):
            ch.query_roundtrip(18123)
        self.assertTrue(sql.call_args_list[-1].args[1].startswith("DROP TABLE"))

    @patch.object(ch, "pick_loopback_port", return_value=18123)
    @patch.object(ch, "clickhouse_ping", return_value=SimpleNamespace(ready=True))
    @patch.object(ch, "query_roundtrip", return_value={"rows": 3, "sum": 60})
    @patch.object(ch, "qualify", return_value={"release_qualified": False})
    @patch.object(ch.subprocess, "Popen")
    def test_server_process_is_bounded_and_terminated(
        self, popen, qualify, roundtrip, _ping, _port
    ):
        child = MagicMock()
        child.poll.return_value = None
        popen.return_value = child
        result = ch.isolated_clickhouse(binary="/path/to/clickhouse")
        self.assertTrue(result["isolated_clickhouse_passed"])
        self.assertFalse(result["release_qualified"])
        self.assertEqual(result["memory_limit_bytes"], 536870912)
        command = popen.call_args.args[0]
        self.assertEqual(command[1], "server")
        self.assertTrue(command[2].startswith("--config-file="))
        qualify.assert_called_once_with(redis_port=6379, clickhouse_port=18123)
        roundtrip.assert_called_once_with(18123)
        child.terminate.assert_called_once()
        child.wait.assert_called_once()

    @patch.object(ch, "pick_loopback_port", return_value=18123)
    @patch.object(ch, "clickhouse_ping", return_value=SimpleNamespace(ready=True))
    @patch.object(ch, "query_roundtrip", side_effect=ValueError("bad data"))
    @patch.object(ch.subprocess, "Popen")
    def test_failure_does_not_leave_process_running(
        self, popen, _query, _ping, _port
    ):
        child = MagicMock()
        child.poll.return_value = None
        popen.return_value = child
        result = ch.isolated_clickhouse(binary="/path/to/clickhouse")
        self.assertFalse(result["isolated_clickhouse_passed"])
        child.terminate.assert_called_once()
        child.wait.assert_called_once()

    @patch.object(ch.shutil, "which", return_value=None)
    def test_unavailable_clickhouse_is_blocked(self, _which):
        result = ch.isolated_clickhouse()
        self.assertFalse(result["isolated_clickhouse_passed"])
        self.assertFalse(result["release_qualified"])


if __name__ == "__main__":
    unittest.main()
