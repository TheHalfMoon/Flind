"""Verify bounded Redis protocol, isolated process lifecycle and fail-closed status."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tools.flind import qualify_ephemeral_redis as smoke


class Stream:
    def __init__(self, reply: bytes):
        self.input = BytesIO(reply)
        self.output = BytesIO()

    def write(self, payload: bytes):
        self.output.write(payload)

    def flush(self):
        pass

    def readline(self, limit: int = -1):
        return self.input.readline(limit)

    def read(self, size: int):
        return self.input.read(size)


class EphemeralRedisWave49Tests(unittest.TestCase):
    def test_resp_set_encoding_and_simple_ok_response(self):
        stream = Stream(b"+OK\r\n")
        self.assertEqual(smoke.redis_command(stream, b"SET", b"key", b"value"), b"OK")
        self.assertEqual(
            stream.output.getvalue(),
            b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n$5\r\nvalue\r\n",
        )

    def test_resp_integer_and_bulk_value(self):
        self.assertEqual(smoke.redis_command(Stream(b":1\r\n"), b"DEL", b"k"), 1)
        self.assertEqual(smoke.redis_command(Stream(b"$5\r\nhello\r\n"), b"GET", b"k"), b"hello")
        self.assertIsNone(smoke.redis_command(Stream(b"$-1\r\n"), b"GET", b"k"))

    def test_resp_rejects_error_unexpected_truncated_and_oversized(self):
        for reply in (b"-ERR unauthorized\r\n", b"!42\r\n", b"$4\r\nabc\r\n",
                      b"$4096\r\n", b"+malformed"):
            with self.subTest(reply=reply):
                with self.assertRaises(ValueError):
                    smoke.redis_command(Stream(reply), b"PING")
        with self.assertRaises(ValueError):
            smoke.redis_command(Stream(b"+OK\r\n"), b"SET", b"k", b"x" * 513)

    @patch.object(smoke.shutil, "which", return_value=None)
    def test_missing_redis_binary_reports_not_qualified(self, _which):
        result = smoke.isolated_redis()
        self.assertFalse(result["isolated_redis_passed"])
        self.assertFalse(result["release_qualified"])

    @patch.object(smoke, "qualify", return_value={"release_qualified": False})
    @patch.object(smoke, "pick_loopback_port", return_value=16379)
    @patch.object(smoke, "redis_ping", return_value=SimpleNamespace(ready=True))
    @patch.object(smoke, "redis_command_check")
    @patch.object(smoke.subprocess, "Popen")
    def test_process_has_explicit_no_persistence_and_always_stops(
        self, popen, commands, _ping, _port, preflight
    ):
        process = MagicMock()
        process.poll.return_value = None
        popen.return_value = process
        result = smoke.isolated_redis(binary="/path/to/redis-server")
        self.assertTrue(result["isolated_redis_passed"])
        self.assertFalse(result["release_qualified"])
        command = popen.call_args.args[0]
        self.assertEqual(command[command.index("--bind") + 1], "127.0.0.1")
        self.assertEqual(command[command.index("--port") + 1], "16379")
        for name, expected in [
            ("--save", ""), ("--appendonly", "no"),
            ("--daemonize", "no"), ("--maxmemory", "64mb"),
            ("--protected-mode", "yes"),
        ]:
            self.assertEqual(command[command.index(name) + 1], expected)
        commands.assert_called_once_with(16379)
        preflight.assert_called_once_with(redis_port=16379)
        self.assertFalse(result["backend_prerequisites"]["release_qualified"])
        process.terminate.assert_called_once()
        process.wait.assert_called_once()

    @patch.object(smoke, "qualify", return_value={"release_qualified": False})
    @patch.object(smoke, "pick_loopback_port", return_value=16379)
    @patch.object(smoke, "redis_ping", return_value=SimpleNamespace(ready=True))
    @patch.object(smoke, "redis_command_check", side_effect=ValueError("failed GET"))
    @patch.object(smoke.subprocess, "Popen")
    def test_failure_stops_temporary_server_and_is_not_pass(
        self, popen, _commands, _ping, _port, preflight
    ):
        process = MagicMock()
        process.poll.return_value = None
        popen.return_value = process
        result = smoke.isolated_redis(binary="/path/to/redis-server")
        self.assertFalse(result["isolated_redis_passed"])
        process.terminate.assert_called_once()
        process.wait.assert_called_once()
        preflight.assert_not_called()

    @patch.object(smoke, "isolated_redis")
    def test_exit_code_reports_failure(self, isolated):
        isolated.return_value = {
            "isolated_redis_passed": False,
            "release_qualified": False,
        }
        with patch("builtins.print"):
            self.assertEqual(smoke.main([]), 2)


if __name__ == "__main__":
    unittest.main()
