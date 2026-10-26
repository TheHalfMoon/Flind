"""Exercise local prereq preflight without contacting any real service."""
from contextlib import redirect_stdout
from io import StringIO
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.flind import qualify_backend_runtime as ready


class FakeSocket:
    def __init__(self, data=b"+PONG\r\n"):
        self.data = data
        self.sent = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def settimeout(self, value):
        self.timeout = value

    def sendall(self, data):
        self.sent = data

    def recv(self, size):
        return self.data


class FakeResponse:
    status = 200

    def read(self, size):
        return b"Ok.\n"


class FakeHttpConnection:
    def __init__(self):
        self.request_args = None
        self.closed = False

    def request(self, method, path):
        self.request_args = (method, path)

    def getresponse(self):
        return FakeResponse()

    def close(self):
        self.closed = True


class BackendRuntimeReadinessWave48Tests(unittest.TestCase):
    @patch.object(ready.shutil, "which", return_value="/usr/bin/psql")
    @patch.object(ready.subprocess, "run")
    def test_postgres_executes_only_readonly_select(self, run, _which):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="1\n", stderr="")
        check = ready.postgres_readonly_sql()
        self.assertTrue(check.ready)
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["-c", "SELECT 1"])
        self.assertIn("-X", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 4)

    def test_python_exact_release_pin_current_environment(self):
        status = ready.pinned_python_version()
        self.assertIn("3.14.7", status.evidence)
        self.assertIn("pinned", status.evidence)
        self.assertEqual(status.ready, tuple(sys.version_info[:3]) == (3, 14, 7))

    def test_python_pin_accepts_exact_patch_version(self):
        status = ready.pinned_python_version(version=(3, 14, 7))
        self.assertTrue(status.ready)
        self.assertIn("matches", status.evidence)

    def test_python_pin_refuses_nearby_patches(self):
        for version in [(3, 14, 6), (3, 14, 8), (3, 13, 7)]:
            with self.subTest(version=version):
                self.assertFalse(ready.pinned_python_version(version=version).ready)

    @patch.object(ready.shutil, "which", return_value=None)
    def test_missing_psql_is_blocked(self, _which):
        self.assertFalse(ready.postgres_readonly_sql().ready)

    @patch.object(ready.shutil, "which", return_value="/usr/bin/psql")
    @patch.object(ready.subprocess, "run", side_effect=subprocess.TimeoutExpired("psql", 4))
    def test_timeout_never_claims_postgres_ready(self, _run, _which):
        self.assertFalse(ready.postgres_readonly_sql().ready)

    @patch.object(ready.socket, "create_connection")
    def test_redis_uses_only_loopback_ping(self, create):
        conn = FakeSocket()
        create.return_value = conn
        check = ready.redis_ping()
        self.assertTrue(check.ready)
        self.assertEqual(create.call_args.args[0], ("127.0.0.1", 6379))
        self.assertEqual(conn.sent, b"*1\r\n$4\r\nPING\r\n")

    @patch.object(ready.socket, "create_connection")
    def test_redis_custom_port_still_loopback_only(self, create):
        create.return_value = FakeSocket()
        self.assertTrue(ready.redis_ping(port=16379).ready)
        self.assertEqual(create.call_args.args[0], ("127.0.0.1", 16379))

    @patch.object(ready.socket, "create_connection")
    def test_redis_auth_failure_is_not_ready(self, create):
        create.return_value = FakeSocket(b"-NOAUTH Authentication required\r\n")
        self.assertFalse(ready.redis_ping().ready)

    @patch.object(ready, "HTTPConnection")
    def test_clickhouse_only_local_ping_without_redirects(self, connection):
        conn = FakeHttpConnection()
        connection.return_value = conn
        self.assertTrue(ready.clickhouse_ping().ready)
        self.assertEqual(connection.call_args.args, ("127.0.0.1", 8123))
        self.assertEqual(conn.request_args, ("GET", "/ping"))
        self.assertTrue(conn.closed)

    @patch.object(ready, "HTTPConnection")
    def test_clickhouse_redirect_is_not_followed(self, connection):
        conn = FakeHttpConnection()
        response = FakeResponse()
        response.status = 302
        conn.getresponse = lambda: response
        connection.return_value = conn
        self.assertFalse(ready.clickhouse_ping().ready)
        self.assertEqual(conn.request_args, ("GET", "/ping"))
        self.assertTrue(conn.closed)

    @patch.object(ready, "HTTPConnection")
    def test_clickhouse_custom_port_is_still_loopback(self, connection):
        client = FakeHttpConnection()
        connection.return_value = client
        self.assertTrue(ready.clickhouse_ping(port=18123).ready)
        self.assertEqual(connection.call_args.args, ("127.0.0.1", 18123))

    @patch.object(ready.importlib.util, "find_spec", return_value=None)
    def test_django_absence_is_reported_not_imported(self, finder):
        self.assertFalse(ready.django_import().ready)
        finder.assert_called_once_with("django")

    @patch.object(ready.shutil, "which", return_value="/usr/bin/docker")
    @patch.object(ready.Path, "exists", return_value=True)
    @patch.object(ready.subprocess, "run")
    def test_docker_is_optional_and_uses_only_unix_socket(self, run, _exists, _which):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="daemon down")
        status = ready.docker_daemon()
        self.assertFalse(status.ready)
        self.assertFalse(status.required)
        command = run.call_args.args[0]
        self.assertEqual(command[1], "--host")
        self.assertTrue(command[2].startswith("unix://"))

    def test_all_prerequisites_can_pass_without_claiming_release_e2e(self):
        names = ("postgres", "redis", "clickhouse", "django")
        with (
            patch.object(ready, "pinned_python_version", return_value=ready.Check("python", True, "ok")),
            patch.object(ready, "postgres_readonly_sql", return_value=ready.Check(names[0], True, "ok")),
            patch.object(ready, "redis_ping", return_value=ready.Check(names[1], True, "ok")),
            patch.object(ready, "clickhouse_ping", return_value=ready.Check(names[2], True, "ok")),
            patch.object(ready, "django_import", return_value=ready.Check(names[3], True, "ok")),
            patch.object(ready, "django_dependency_lock", return_value=ready.Check("django_lock", True, "locked")),
            patch.object(ready, "docker_daemon", return_value=ready.Check("docker", False, "off", required=False)),
        ):
            result = ready.qualify()
        self.assertTrue(result["prerequisites_ready"])
        self.assertFalse(result["release_qualified"])
        self.assertEqual(result["blocked_by"], [])

    @patch.object(ready, "audit_runtime_lock")
    def test_django_import_is_not_sufficient_when_lock_is_incomplete(self, lock):
        lock.return_value = {
            "direct_lock_qualified": False,
            "applicable_direct_dependencies": 201,
            "installed_locked_direct_dependencies": 1,
            "missing_count": 198,
            "version_mismatch_count": 2,
            "unverified_marker_count": 0,
            "unlocked_count": 0,
        }
        status = ready.django_dependency_lock()
        self.assertEqual(status.name, "django_lock")
        self.assertFalse(status.ready)
        self.assertTrue(status.required)
        self.assertIn("1/201", status.evidence)
        self.assertIn("missing 198", status.evidence)

    @patch.object(ready, "audit_runtime_lock")
    def test_full_direct_lock_allows_backend_lock_check(self, lock):
        lock.return_value = {
            "direct_lock_qualified": True,
            "applicable_direct_dependencies": 201,
            "installed_locked_direct_dependencies": 201,
            "missing_count": 0,
            "version_mismatch_count": 0,
            "unverified_marker_count": 0,
            "unlocked_count": 0,
        }
        self.assertTrue(ready.django_dependency_lock().ready)

    @patch.object(ready, "audit_runtime_lock", side_effect=ValueError("PRIVATE_TOKEN"))
    def test_dependency_audit_refuses_and_redacts_internal_error(self, _lock):
        status = ready.django_dependency_lock()
        self.assertFalse(status.ready)
        self.assertNotIn("PRIVATE_TOKEN", status.evidence)

    def test_incomplete_lock_keeps_prerequisites_blocked_even_with_django(self):
        with (
            patch.object(ready, "pinned_python_version", return_value=ready.Check("python", True, "ok")),
            patch.object(ready, "postgres_readonly_sql", return_value=ready.Check("postgres", True, "ok")),
            patch.object(ready, "redis_ping", return_value=ready.Check("redis", True, "ok")),
            patch.object(ready, "clickhouse_ping", return_value=ready.Check("clickhouse", True, "ok")),
            patch.object(ready, "django_import", return_value=ready.Check("django", True, "ok")),
            patch.object(ready, "django_dependency_lock", return_value=ready.Check("django_lock", False, "missing")),
            patch.object(ready, "docker_daemon", return_value=ready.Check("docker", False, "off", required=False)),
        ):
            result = ready.qualify()
        self.assertFalse(result["prerequisites_ready"])
        self.assertEqual(result["blocked_by"], ["django_lock"])
        self.assertFalse(result["release_qualified"])

    @patch.object(ready, "qualify")
    def test_human_output_calls_out_optional_docker(self, qualify):
        qualify.return_value = {
            "prerequisites_ready": False,
            "release_qualified": False,
            "blocked_by": ["redis"],
            "checks": [
                {"name": "redis", "ready": False, "required": True, "evidence": "offline"},
                {"name": "docker", "ready": False, "required": False, "evidence": "offline"},
            ],
        }
        buf = StringIO()
        with redirect_stdout(buf):
            code = ready.main([])
        self.assertEqual(code, 2)
        self.assertIn("redis: BLOCKED", buf.getvalue())
        self.assertIn("docker: OPTIONAL/UNAVAILABLE", buf.getvalue())
        self.assertIn("Release E2E: NOT QUALIFIED", buf.getvalue())

    @patch.object(ready, "qualify")
    def test_json_blocker_exit_is_machine_readable_and_nonzero(self, qualify):
        qualify.return_value = {
            "prerequisites_ready": False,
            "release_qualified": False,
            "blocked_by": ["django"],
            "checks": [],
        }
        buf = StringIO()
        with redirect_stdout(buf):
            exit_code = ready.main(["--json"])
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(buf.getvalue())["blocked_by"], ["django"])


if __name__ == "__main__":
    unittest.main()
