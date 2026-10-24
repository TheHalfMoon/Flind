"""Verify Flind server version requirements from source, not hardcoded hopes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest
from unittest.mock import patch

from tools.flind import qualify_service_versions as versions


class ServiceVersionsWave51Tests(unittest.TestCase):
    def test_extract_exact_production_contract_from_project_settings(self):
        self.assertEqual(
            versions.source_requirements(),
            {
                "postgresql": ">=14.0.0",
                "redis": ">=7.0.0,<8.0.0",
                "clickhouse": ">=24.8,<=25.12",
            },
        )

    def test_runtime_semver_acceptance_and_decline(self):
        cases = [
            ("13.13.9", ">=14.0.0", False),
            ("17.9 (Homebrew)", ">=14.0.0", True),
            ("7.2.4", ">=7.0.0,<8.0.0", True),
            ("8.10.2", ">=7.0.0,<8.0.0", False),
            ("24.8.15.4", ">=24.8,<=25.12", True),
            ("25.12", ">=24.8,<=25.12", True),
            ("25.12.1", ">=24.8,<=25.12", True),
            ("25.12.99", ">=24.8,<=25.12", True),
            ("25.13.0", ">=24.8,<=25.12", False),
            ("26.10.2.103", ">=24.8,<=25.12", False),
        ]
        for value, spec, expected in cases:
            with self.subTest(value=value, spec=spec):
                self.assertEqual(versions.version_matches_spec(value, spec), expected)

    def test_unparsable_and_ambiguous_versions_fail_closed(self):
        for value in ("", "version unknown", "abc.3", "v6-unsafe"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    versions.parse_version(value)
        with self.assertRaises(ValueError):
            versions.version_matches_spec("7.2.4", "^7.0")

    def test_settings_parser_rejects_missing_requirements(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "service_requirements.py"
            path.write_text('ServiceVersionRequirement(service="redis", supported_version=">=7")')
            with self.assertRaises(ValueError):
                versions.source_requirements(path)

    def test_settings_parser_rejects_duplicate_and_unknown_service(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "service_requirements.py"
            path.write_text(
                'ServiceVersionRequirement(service="redis", supported_version=">=7")\n'
                'ServiceVersionRequirement(service="redis", supported_version=">=8")\n'
            )
            with self.assertRaises(ValueError):
                versions.source_requirements(path)

    @patch.object(versions, "postgres_version")
    @patch.object(versions, "redis_version")
    @patch.object(versions, "clickhouse_version")
    def test_unsupported_engines_do_not_pass_even_when_alive(self, ch, redis, pg):
        pg.return_value = "17.9"
        redis.return_value = "8.10.2"
        ch.return_value = "26.10.2.103"
        result = versions.qualify_service_versions(16379, 18123)
        self.assertFalse(result["version_requirements_met"])
        self.assertFalse(result["release_qualified"])
        self.assertEqual(result["blocked_by"], ["redis", "clickhouse"])
        redis.assert_called_once_with(16379)
        ch.assert_called_once_with(18123)

    @patch.object(versions, "postgres_version", return_value="17.9")
    @patch.object(versions, "redis_version", return_value="7.2.4")
    @patch.object(versions, "clickhouse_version", return_value="25.12")
    def test_supported_versions_are_only_component_qualified(self, *_):
        result = versions.qualify_service_versions(16379, 18123)
        self.assertTrue(result["version_requirements_met"])
        self.assertFalse(result["release_qualified"])

    @patch.object(versions, "postgres_version", return_value="17.9")
    @patch.object(versions, "redis_version", side_effect=OSError("offline"))
    @patch.object(versions, "clickhouse_version", return_value="25.12")
    def test_unreachable_service_fails_closed(self, *_):
        result = versions.qualify_service_versions(16379, 18123)
        self.assertIn("redis", result["blocked_by"])
        self.assertFalse(result["version_requirements_met"])

    @patch.object(versions.subprocess, "run")
    def test_postgres_query_read_only_and_forced_loopback(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="17.9\n", stderr="")
        self.assertEqual(versions.postgres_version(), "17.9")
        command = run.call_args.args[0]
        self.assertIn("127.0.0.1", command)
        self.assertEqual(command[-2:], ["-c", "SHOW server_version"])

    @patch.object(versions, "sql_http", return_value=b"26.10.2.103\n")
    def test_clickhouse_version_uses_direct_local_sql(self, http):
        self.assertEqual(versions.clickhouse_version(18123), "26.10.2.103")
        http.assert_called_once_with(18123, "SELECT version()")


if __name__ == "__main__":
    unittest.main()
