"""Wave225: fail-closed original service E2E admission under Python -O.

All fixtures are synthetic; this module starts no Docker, PostgreSQL, Redis or ClickHouse.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import runpy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.flind.e2e import verify_wave216 as subject


def owned(service="postgres"):
    ports = {"postgres": "5432/tcp", "redis": "6379/tcp", "clickhouse": "8123/tcp"}
    return {
        "Config": {"Labels": {
            "com.docker.compose.project": "flindwave216",
            "com.docker.compose.service": service,
        }},
        "State": {"Running": True, "Health": {"Status": "healthy"}},
        "NetworkSettings": {"Ports": {
            ports[service]: [{"HostIp": "127.0.0.1", "HostPort": str(subject.SERVICES[service])}]
        }},
    }


class Wave225OptimizedAdmissionTests(unittest.TestCase):
    def test_only_matching_owned_service_admitted(self):
        for service in subject.SERVICES:
            with self.subTest(service=service):
                self.assertIsNone(subject.assert_owned_service(service, owned(service)))

    def test_foreign_project_rejected(self):
        item = owned()
        item["Config"]["Labels"]["com.docker.compose.project"] = "zyara"
        with self.assertRaisesRegex(AssertionError, "wrong Compose project"):
            subject.assert_owned_service("postgres", item)

    def test_foreign_service_and_unhealthy_container_rejected(self):
        for field, change, message in (
            ("Config", lambda x: x["Labels"].update({"com.docker.compose.service": "foreign"}), "wrong service"),
            ("State", lambda x: x.update({"Running": False}), "not running"),
            ("State", lambda x: x["Health"].update({"Status": "starting"}), "unhealthy"),
        ):
            item = owned()
            change(item[field])
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                subject.assert_owned_service("postgres", item)

    def test_loopback_and_port_mapping_fail_closed(self):
        for host, port, message in (
            ("0.0.0.0", "15439", "beyond loopback"),
            ("::", "15439", "beyond loopback"),
            ("127.0.0.1", "5432", "unexpected host port"),
        ):
            item = owned()
            item["NetworkSettings"]["Ports"]["5432/tcp"] = [
                {"HostIp": host, "HostPort": port}
            ]
            with self.subTest(host=host, port=port), self.assertRaisesRegex(AssertionError, message):
                subject.assert_owned_service("postgres", item)
        item = owned()
        item["NetworkSettings"]["Ports"]["5432/tcp"] = []
        with self.assertRaisesRegex(AssertionError, "unexpected port mappings"):
            subject.assert_owned_service("postgres", item)

    def test_missing_postgres_databases_are_rejected(self):
        result = SimpleNamespace(stdout="test_posthog\ntest_persons\n")
        with patch.object(subject.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(AssertionError, "isolated PG test databases missing"):
                subject.read_database_names()

    def test_redis_pong_is_really_checked(self):
        with patch.object(subject.subprocess, "run", return_value=SimpleNamespace(stdout="NOPE\n")):
            with self.assertRaisesRegex(AssertionError, "isolated Redis unavailable"):
                subject.check_redis()

    def test_clickhouse_database_identity_is_really_checked(self):
        with patch.object(subject.urllib.request, "urlopen", return_value=io.BytesIO(b"customer_db\n")):
            with self.assertRaisesRegex(AssertionError, "wrong ClickHouse database"):
                subject.check_clickhouse()

    def test_original_synthetic_clickhouse_readback_denied_and_cleaned(self):
        calls = []
        def fake_sql(query):
            calls.append(query)
            if query.startswith("SELECT count()"):
                return "0"
            return ""
        with patch.object(subject, "clickhouse_sql", side_effect=fake_sql):
            with self.assertRaisesRegex(AssertionError, "tenant 101 not isolated"):
                subject.check_synthetic_clickhouse_write()
        self.assertEqual(len([x for x in calls if x.startswith("SELECT count()")]), 1)
        self.assertTrue(calls[-1].startswith("DROP TABLE flind_w216_probe_"))

    def test_synthetic_clickhouse_denies_wrong_second_tenant_and_total(self):
        for mismatch, expected_error in (
            ("tenant202", "tenant 202 not isolated"),
            ("total", "row count mismatch"),
        ):
            calls = []

            def fake_sql(query):
                calls.append(query)
                if query.startswith("SELECT count()"):
                    if "team_id=101" in query:
                        return "1"
                    if "team_id=202" in query:
                        return "0" if mismatch == "tenant202" else "1"
                    return "0" if mismatch == "total" else "2"
                return ""

            with self.subTest(mismatch=mismatch), patch.object(
                subject, "clickhouse_sql", side_effect=fake_sql
            ):
                with self.assertRaisesRegex(AssertionError, expected_error):
                    subject.check_synthetic_clickhouse_write()
            self.assertTrue(calls[-1].startswith("DROP TABLE flind_w216_probe_"))

    def test_original_synthetic_clickhouse_all_readbacks_executed(self):
        calls = []
        def fake_sql(query):
            calls.append(query)
            if query.startswith("SELECT count()"):
                return "2" if "WHERE" not in query else "1"
            return ""
        with patch.object(subject, "clickhouse_sql", side_effect=fake_sql):
            self.assertTrue(subject.check_synthetic_clickhouse_write())
        self.assertEqual(len([x for x in calls if x.startswith("SELECT count()")]), 3)
        self.assertTrue(calls[-1].startswith("DROP TABLE flind_w216_probe_"))

    def test_optimized_cli_rejects_unrecognized_write_probe_flags(self):
        program = Path(subject.__file__)
        stderr = io.StringIO()
        recorded = []
        expected = {"test_posthog", "test_persons", "test_behavioral_cohorts", "test_cyclotron_node"}

        def synthetic_docker(args, **kwargs):
            recorded.append(args)
            if args[:2] == ["docker", "inspect"]:
                service = args[2].split("-")[-2]
                return SimpleNamespace(stdout=json.dumps([owned(service)]))
            if "redis-cli" in args:
                return SimpleNamespace(stdout="PONG\n")
            if "psql" in args:
                return SimpleNamespace(stdout="\n".join(sorted(expected)) + "\n")
            raise AssertionError("Unexpected Docker command")

        with patch.object(subject.subprocess, "run", side_effect=synthetic_docker):
            with patch.object(
                subject.urllib.request, "urlopen", return_value=io.BytesIO(b"flind_test_wave216abc123\n")
            ):
                with patch.object(sys, "argv", [str(program), "--synthetic-clickhouse-write-probe", "--unknown"]):
                    with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                        runpy.run_path(str(program), run_name="__main__")
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("unknown arguments", stderr.getvalue())
        self.assertEqual(sum("inspect" in cmd for cmd in recorded), 3)

    def test_no_compiler_strippable_asserts_remain(self):
        source = Path(subject.__file__).read_text(encoding="utf-8")
        self.assertFalse([n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert)])

    def test_optimized_python_runtime_is_exercised(self):
        # This is genuinely a different Python process with optimizations on.
        self.assertEqual(__debug__, sys.flags.optimize == 0)


if __name__ == "__main__":
    unittest.main()
