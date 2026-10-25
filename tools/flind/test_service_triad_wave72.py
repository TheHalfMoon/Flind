"""Wave 72: exact scoped Django + three isolated services, fail-closed receipts."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.flind import qualify_service_triad_wave72 as triad


def good_auth():
    return {
        "django_framework_auth_session_qualified": True,
        "stages": [
            {"app": "auth", "command_completed": True},
            {"app": "posthog_session", "command_completed": True},
        ],
    }


class PrivateServiceTriadWave72Tests(unittest.TestCase):
    @patch.object(triad, "isolated_postgres")
    @patch.object(triad, "audit_runtime_lock", return_value={
        "direct_lock_qualified": False,
    })
    def test_unqualified_python_lock_cannot_start_database(self, _lock, postgres):
        result = triad.qualify_private_triad()
        self.assertFalse(result["three_service_scoped_auth_qualified"])
        self.assertFalse(result["release_qualified"])
        postgres.assert_not_called()

    @patch.object(triad, "migrate_auth_and_sessions")
    @patch.object(triad, "isolated_redis")
    def test_nested_clickhouse_runs_while_redis_and_postgres_still_alive(self, redis, auth):
        auth.return_value = good_auth()
        calls = []

        def start_redis(*, on_ready):
            calls.append("redis")
            return {
                "isolated_redis_passed": True,
                "nested_clickhouse": on_ready(16431),
            }

        redis.side_effect = start_redis
        with patch.object(triad, "isolated_clickhouse", return_value={
            "isolated_clickhouse_passed": True,
            "http_query_roundtrip": {"rows": 3, "sum": 60},
            "service_versions": {"checks": [{"service": "redis", "version": "7.4.5"}, {"service": "clickhouse", "version": "25.8.0"}]},
        }) as clickhouse:
            receipt = triad.private_service_probe(
                16542, "private-credential", "flind_ephemeral",
            )

        auth.assert_called_once_with(16542, "private-credential", "flind_ephemeral")
        self.assertEqual(calls, ["redis"])
        clickhouse.assert_called_once_with(redis_port=16431)
        self.assertTrue(receipt["framework_auth_session_schema_passed"])
        self.assertTrue(receipt["redis_and_clickhouse_overlapped_postgres"])
        self.assertEqual(receipt["observed_service_versions"]["redis"], "7.4.5")
        self.assertEqual(len(receipt["framework_scoped_migration_stages"]), 2)
        self.assertNotIn("private-credential", str(receipt))
        self.assertNotIn("16542", str(receipt))

    @patch.object(triad, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(triad, "isolated_postgres")
    def test_all_components_make_scoped_receipt_pass_without_release(self, postgres, _lock):
        def run_callback(*, on_ready):
            scoped = {
                "framework_auth_session_schema_passed": True,
                "redis_isolated_passed": True,
                "clickhouse_isolated_passed": True,
                "clickhouse_http_sql_readback_passed": True,
                "redis_and_clickhouse_overlapped_postgres": True,
                "observed_service_versions": {"redis": "7.4.5", "clickhouse": "25.8.0"},
                "framework_scoped_migration_stages": [],
            }
            return {"postgres_component_passed": True, "postgres_version": "17.9", "django_migration_plan": scoped}
        postgres.side_effect = run_callback
        with patch.object(triad, "source_requirements", return_value={
            "postgresql": ">=14.0.0", "redis": ">=7.0.0,<8.0.0", "clickhouse": ">=24.8,<=25.12",
        }):
            result = triad.qualify_private_triad()
        self.assertTrue(result["three_service_reachability_passed"])
        self.assertTrue(result["service_versions_qualified"])
        self.assertTrue(result["three_service_scoped_auth_qualified"])
        self.assertFalse(result["sdk_event_ingestion_qualified"])
        self.assertFalse(result["full_django_schema_qualified"])
        self.assertFalse(result["tenant_isolation_qualified"])
        self.assertFalse(result["release_qualified"])

    @patch.object(triad, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(triad, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "postgres_version": "17.9",
        "django_migration_plan": {
            "framework_auth_session_schema_passed": True,
            "redis_isolated_passed": True,
            "clickhouse_isolated_passed": True,
            "clickhouse_http_sql_readback_passed": True,
            "redis_and_clickhouse_overlapped_postgres": True,
            "observed_service_versions": {
                "redis": "8.10.2", "clickhouse": "26.10.2.103",
            },
        },
    })
    def test_newer_incompatible_versions_block_qualification_even_when_sql_passes(self, _pg, _lock):
        with patch.object(triad, "source_requirements", return_value={
            "postgresql": ">=14.0.0", "redis": ">=7.0.0,<8.0.0",
            "clickhouse": ">=24.8,<=25.12",
        }):
            receipt = triad.qualify_private_triad()
        self.assertTrue(receipt["three_service_reachability_passed"])
        self.assertFalse(receipt["service_versions_qualified"])
        self.assertFalse(receipt["three_service_scoped_auth_qualified"])
        self.assertFalse(receipt["release_qualified"])
        self.assertEqual(receipt["observed_service_versions"]["redis"], "8.10.2")

    @patch.object(triad, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(triad, "isolated_postgres", return_value={
        "postgres_component_passed": False,
        "django_migration_plan": {
            "framework_auth_session_schema_passed": True,
            "redis_isolated_passed": True,
            "clickhouse_isolated_passed": True,
            "clickhouse_http_sql_readback_passed": True,
            "redis_and_clickhouse_overlapped_postgres": True,
        },
    })
    def test_postgres_failure_overrides_inconsistent_child(self, _pg, _lock):
        result = triad.qualify_private_triad()
        self.assertFalse(result["postgres_17_isolated_passed"])
        self.assertFalse(result["three_service_scoped_auth_qualified"])

    @patch.object(triad, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(triad, "isolated_postgres", return_value={
        "postgres_component_passed": True,
        "django_migration_plan": {
            "framework_auth_session_schema_passed": True,
            "redis_isolated_passed": True,
            "clickhouse_isolated_passed": True,
            "clickhouse_http_sql_readback_passed": False,
            "redis_and_clickhouse_overlapped_postgres": True,
        },
    })
    def test_broken_clickhouse_readback_blocks_scoped_pass(self, _pg, _lock):
        result = triad.qualify_private_triad()
        self.assertFalse(result["three_service_scoped_auth_qualified"])
        self.assertFalse(result["release_qualified"])

    @patch.object(triad, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(triad, "isolated_postgres", return_value={
        "postgres_component_passed": True,
    })
    def test_missing_private_probe_receipt_fails_closed(self, _pg, _lock):
        result = triad.qualify_private_triad()
        self.assertFalse(result["three_service_scoped_auth_qualified"])
        self.assertEqual(result["framework_scoped_migration_stages"], [])

    @patch.object(triad, "audit_runtime_lock")
    @patch.object(triad, "isolated_postgres")
    def test_nonabsolute_or_unavailable_binary_fails_before_services(self, postgres, lock):
        for candidate in ("redis-server", "/nonexistent/flind-redis", ""):
            with self.subTest(candidate=candidate):
                receipt = triad.qualify_private_triad(redis_binary=candidate)
                self.assertFalse(receipt["three_service_scoped_auth_qualified"])
        lock.assert_not_called()
        postgres.assert_not_called()

    @patch.object(triad, "migrate_auth_and_sessions", return_value={
        "django_framework_auth_session_qualified": True,
    })
    @patch.object(triad, "isolated_redis")
    @patch.object(triad, "isolated_clickhouse")
    def test_explicit_binary_paths_pass_only_to_private_service_wrappers(self, clickhouse, redis, _auth):
        redis.side_effect = lambda *, binary, on_ready: {
            "isolated_redis_passed": True,
            "nested_clickhouse": on_ready(16499),
        }
        clickhouse.return_value = {
            "isolated_clickhouse_passed": True,
            "http_query_roundtrip": {"rows": 3, "sum": 60},
        }
        receipt = triad.private_service_probe(
            16544, "synthetic-private", "flind_ephemeral",
            redis_binary="/usr/local/bin/redis-server7",
            clickhouse_binary="/usr/local/bin/clickhouse25",
        )
        self.assertTrue(receipt["redis_isolated_passed"])
        redis.assert_called_once()
        self.assertEqual(redis.call_args.kwargs["binary"], "/usr/local/bin/redis-server7")
        clickhouse.assert_called_once_with(
            redis_port=16499, binary="/usr/local/bin/clickhouse25",
        )
        self.assertNotIn("synthetic-private", str(receipt))

    @patch.object(triad, "audit_runtime_lock", return_value={
        "direct_lock_qualified": True,
    })
    @patch.object(triad, "isolated_postgres")
    @patch.object(triad, "private_service_probe")
    def test_selection_requires_local_executable_file(self, probe, postgres, _lock):
        with tempfile.TemporaryDirectory() as directory:
            redis = Path(directory) / "redis-server7"
            ch = Path(directory) / "clickhouse25"
            redis.write_bytes(b"synthetic-not-executed")
            ch.write_bytes(b"synthetic-not-executed")
            redis.chmod(0o700)
            ch.chmod(0o700)
            self.assertTrue(triad.selected_local_binary_is_valid(str(redis)))
            self.assertTrue(triad.selected_local_binary_is_valid(str(ch)))
            postgres.side_effect = lambda *, on_ready: {
                "postgres_component_passed": True,
                "django_migration_plan": on_ready(16544, "synthetic-secret", "flind_ephemeral"),
            }
            probe.return_value = {}
            report = triad.qualify_private_triad(str(redis), str(ch))
            self.assertFalse(report["three_service_scoped_auth_qualified"])
            probe.assert_called_once_with(
                16544, "synthetic-secret", "flind_ephemeral",
                redis_binary=str(redis), clickhouse_binary=str(ch),
            )
            redis.chmod(0o600)
            self.assertFalse(triad.selected_local_binary_is_valid(str(redis)))

    @patch.object(triad, "qualify_private_triad", return_value={
        **triad.closed_receipt(),
    })
    def test_cli_accepts_explicit_local_executable_paths(self, qualify):
        with redirect_stdout(io.StringIO()):
            code = triad.main([
                "--json", "--redis-bin", "/path/to/redis-server7",
                "--clickhouse-bin", "/path/to/clickhouse25",
            ])
        self.assertEqual(code, 2)
        qualify.assert_called_once_with(
            "/path/to/redis-server7", "/path/to/clickhouse25",
        )

    @patch.object(triad, "qualify_private_triad", return_value={
        **triad.closed_receipt(),
        "blocker": "Synthetic unavailable",
    })
    def test_failed_cli_returns_nonzero_json_receipt(self, _qualify):
        with redirect_stdout(io.StringIO()) as out:
            code = triad.main(["--json"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out.getvalue())["release_qualified"])


if __name__ == "__main__":
    unittest.main()
