"""Wave 101 guards for simultaneous isolated Kafka, PG, Redis, ClickHouse proof."""
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import unittest

from tools.flind import qualify_four_native_services_wave101 as q

REQ = {"postgresql": ">=14.0.0", "redis": ">=7.0.0,<8.0.0",
       "clickhouse": ">=24.8,<=25.12"}
HOME = Path("/synthetic/kafka")
REDIS = "/synthetic/redis-server"
CH = "/synthetic/clickhouse"


def admission():
    stack = ExitStack()
    stack.enter_context(patch.object(q, "audit_runtime_lock",
                                     return_value={"direct_lock_qualified": True}))
    stack.enter_context(patch.object(q, "source_requirements", return_value=REQ))
    stack.enter_context(patch.object(q, "qualify_binary_versions",
                                     return_value={"service_binary_versions_qualified": True}))
    stack.enter_context(patch.object(q, "kafka_paths", return_value={}))
    return stack


class FourNativeServicesWave101(unittest.TestCase):
    def test_unlocked_django_fails_before_any_daemon(self):
        with patch.object(q, "audit_runtime_lock", return_value={"direct_lock_qualified": False}):
            with patch.object(q, "qualify_kafka") as kafka:
                result = q.qualify_four_services(HOME, REDIS, CH)
        self.assertFalse(result["four_native_services_synthetic_qualified"])
        kafka.assert_not_called()

    def test_unsupported_clickhouse_fails_before_kafka(self):
        with admission(), patch.object(q, "qualify_binary_versions",
                                       return_value={"service_binary_versions_qualified": False}):
            with patch.object(q, "qualify_kafka") as kafka:
                result = q.qualify_four_services(HOME, REDIS, CH)
        self.assertFalse(result["four_native_services_synthetic_qualified"])
        kafka.assert_not_called()

    def test_missing_kafka_tools_fails_before_start(self):
        with admission(), patch.object(q, "kafka_paths", side_effect=ValueError("missing")):
            with patch.object(q, "qualify_kafka") as kafka:
                result = q.qualify_four_services(HOME, REDIS, CH)
        self.assertFalse(result["four_native_services_synthetic_qualified"])
        kafka.assert_not_called()

    def _complete(self, *, actual_ch_version=b"25.12.7.21",
                  pg_version="17.9", forged_pg=False, wrong_events=False):
        def on_clickhouse(*, binary, redis_port, on_ready):
            self.assertEqual(binary, CH)
            event_receipt = on_ready(61234)
            return {"isolated_clickhouse_passed": True,
                    "event_readback": event_receipt,
                    "http_query_roundtrip": {"rows": 3, "sum": 60},
                    "service_versions": {"checks": [
                        {"service": "redis", "version": "7.4.11"},
                        {"service": "clickhouse", "version": "25.12.7.21"},
                    ]}}

        def on_redis(*, binary, on_ready):
            self.assertEqual(binary, REDIS)
            return {"isolated_redis_passed": True, "nested_clickhouse": on_ready(61235)}

        def on_postgres(*, on_ready):
            receipt = on_ready(61236, "private-credential", "flind_temp")
            return {"postgres_component_passed": True,
                    "postgres_version": pg_version,
                    "django_migration_plan": receipt}

        def on_kafka(home, *, on_consumed):
            fixture = q.EVENTS
            if wrong_events:
                fixture = ({**fixture[0], "team_id": 999},) + fixture[1:]
                with self.assertRaises(ValueError):
                    on_consumed(fixture)
                return {"isolated_kafka_passed": False}
            return {"isolated_kafka_passed": not forged_pg,
                    "exact_json_message_roundtrip": True,
                    "synthetic_events_consumed": 3,
                    "synthetic_relay": on_consumed(fixture)}

        with admission(), patch.object(q, "migrate_auth_and_sessions", return_value={
            "django_framework_auth_session_qualified": True,
        }), patch.object(q, "sql_http", return_value=actual_ch_version), patch.object(
            q, "relay_readback", return_value={
                "synthetic_relay_passed": True,
                "cross_team_path_reads_absent": True,
                "kafka_records_replayed": 3,
            }), patch.object(q, "isolated_clickhouse", side_effect=on_clickhouse), patch.object(
            q, "isolated_redis", side_effect=on_redis), patch.object(
            q, "isolated_postgres", side_effect=on_postgres), patch.object(
            q, "qualify_kafka", side_effect=on_kafka):
            return q.qualify_four_services(HOME, REDIS, CH)

    def test_exact_four_service_callback_is_qualified(self):
        receipt = self._complete()
        self.assertTrue(receipt["four_native_services_synthetic_qualified"])
        for key in ("exact_python_lock_passed", "kafka_431_transport_passed",
                    "postgres_scoped_django_auth_passed", "redis_7_private_store_passed",
                    "clickhouse_supported_sql_passed", "three_exact_events_replayed",
                    "cross_team_sql_filters_passed", "all_service_versions_supported"):
            self.assertIs(receipt[key], True, key)
        for key in ("production_capture_rust_qualified", "production_sdk_http_qualified",
                    "production_kafka_ingester_qualified", "production_events_schema_qualified",
                    "production_query_api_qualified", "production_tenant_authorization_qualified",
                    "dashboard_e2e_qualified", "release_qualified"):
            self.assertIs(receipt[key], False, key)

    def test_not_a_success_if_kafka_component_failed(self):
        result = self._complete(forged_pg=True)
        self.assertFalse(result["four_native_services_synthetic_qualified"])

    def test_not_a_success_if_postgres_version_wrong(self):
        receipt = self._complete(pg_version="13.1")
        self.assertFalse(receipt["four_native_services_synthetic_qualified"])

    def test_tampered_events_never_reach_postgres(self):
        # The forged test simulates native Kafka returning a fixture mismatch;
        # production coordinator must fail before the PostgreSQL callback.
        with admission(), patch.object(q, "isolated_postgres") as pg:
            def fake_kafka(home, *, on_consumed):
                with self.assertRaises(ValueError):
                    on_consumed(({**q.EVENTS[0], "team_id": 999},) + q.EVENTS[1:])
                return {"isolated_kafka_passed": False}
            with patch.object(q, "qualify_kafka", side_effect=fake_kafka):
                out = q.qualify_four_services(HOME, REDIS, CH)
        self.assertFalse(out["four_native_services_synthetic_qualified"])
        pg.assert_not_called()

    def test_fail_closed_without_source_version_contract(self):
        with patch.object(q, "source_requirements", side_effect=ValueError("missing")), patch.object(q, "qualify_kafka") as kafka:
            out = q.qualify_four_services(HOME, REDIS, CH)
        self.assertFalse(out["four_native_services_synthetic_qualified"])
        kafka.assert_not_called()

    def test_release_flags_remain_false(self):
        text = Path(q.__file__).read_text()
        self.assertIn('"release_qualified": False', text)
        self.assertIn('"production_capture_rust_qualified": False', text)
        self.assertIn("on_consumed=_on_consumed", text)
        self.assertIn("relay_readback(ch_port, records)", text)


if __name__ == "__main__":
    unittest.main()
