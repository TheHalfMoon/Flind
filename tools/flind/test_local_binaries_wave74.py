"""Wave 74 local supported-service binary preflight safety tests."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_local_binaries_wave74 as probe


SPECS = {
    "postgresql": ">=14.0.0",
    "redis": ">=7.0.0,<8.0.0",
    "clickhouse": ">=24.8,<=25.12",
}


class LocalBinaryWave74Tests(unittest.TestCase):
    def test_invalid_service_is_refused(self):
        receipt = probe.inspect_binary("bogus", "/usr/bin/false", "<99")
        self.assertFalse(receipt["supported_version"])

    def test_relative_binary_fails_without_running_process(self):
        with patch.object(probe.subprocess, "run") as run:
            self.assertFalse(probe.inspect_binary("redis", "redis-server", SPECS["redis"])["supported_version"])
            run.assert_not_called()

    def test_missing_absolute_binary_fails_closed(self):
        with patch.object(probe.subprocess, "run") as run:
            result = probe.inspect_binary("clickhouse", "/impossible/not-installed", SPECS["clickhouse"])
            self.assertFalse(result["binary_exists_and_executable"])
            run.assert_not_called()

    def test_nonexecutable_binary_never_invoked(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "server"
            file.write_text("no")
            file.chmod(0o600)
            with patch.object(probe.subprocess, "run") as run:
                self.assertFalse(probe.inspect_binary("redis", str(file), SPECS["redis"])["supported_version"])
                run.assert_not_called()

    def test_valid_redis7_and_clickhouse25_are_admitted(self):
        with patch.object(probe, "source_requirements", return_value=SPECS):
            with patch.object(probe, "inspect_binary", side_effect=[
                {"service": "redis", "supported_version": True, "observed_version": "7.4.11"},
                {"service": "clickhouse", "supported_version": True, "observed_version": "25.12.7.21"},
            ]) as inspect:
                result = probe.qualify_binary_versions("/tmp/redis7", "/tmp/clickhouse25")
        self.assertTrue(result["service_binary_versions_qualified"])
        self.assertFalse(result["runtime_service_qualified"])
        self.assertFalse(result["release_qualified"])
        self.assertEqual(inspect.call_count, 2)

    def test_incompatible_redis8_or_clickhouse26_refuses_admission(self):
        with patch.object(probe, "source_requirements", return_value=SPECS):
            for checks in ((True, False), (False, True)):
                with self.subTest(checks=checks), patch.object(probe, "inspect_binary", side_effect=[
                    {"supported_version": checks[0]}, {"supported_version": checks[1]},
                ]):
                    self.assertFalse(
                        probe.qualify_binary_versions("redis", "clickhouse")["service_binary_versions_qualified"]
                    )

    def test_missing_settings_never_makes_success(self):
        with patch.object(probe, "source_requirements", side_effect=FileNotFoundError):
            result = probe.qualify_binary_versions("redis", "clickhouse")
        self.assertFalse(result["service_binary_versions_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_process_execution_is_bounded_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "redis-server"
            file.write_text("#!/bin/sh")
            file.chmod(0o700)
            response = subprocess.CompletedProcess([str(file), "--version"], 0,
                                                   "Redis server v=7.4.11 sha=test", "")
            with patch.object(probe.subprocess, "run", return_value=response) as run:
                result = probe.inspect_binary("redis", str(file), SPECS["redis"])
            self.assertTrue(result["supported_version"])
            self.assertEqual(run.call_args.args[0], [str(file), "--version"])
            self.assertFalse(run.call_args.kwargs["check"])
            self.assertEqual(run.call_args.kwargs["timeout"], 55)
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_bounded_output_rejects_flood(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "clickhouse"
            file.write_text("x")
            file.chmod(0o700)
            response = subprocess.CompletedProcess([str(file), "--version"], 0,
                "ClickHouse local version 25.12.7.21" + "z" * 5000, "")
            with patch.object(probe.subprocess, "run", return_value=response):
                result = probe.inspect_binary("clickhouse", str(file), SPECS["clickhouse"])
            self.assertFalse(result["supported_version"])

    def test_timeout_never_qualifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "clickhouse"
            file.write_text("x")
            file.chmod(0o700)
            with patch.object(probe.subprocess, "run", side_effect=subprocess.TimeoutExpired("clickhouse", 55)):
                result = probe.inspect_binary("clickhouse", str(file), SPECS["clickhouse"])
            self.assertFalse(result["supported_version"])


if __name__ == "__main__":
    unittest.main()
