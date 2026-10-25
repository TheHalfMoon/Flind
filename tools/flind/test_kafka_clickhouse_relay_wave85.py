"""Guardrails for the synthetic Kafka CLI -> temporary ClickHouse relay."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_kafka_clickhouse_relay_wave85 as q


class SyntheticKafkaClickHouseRelay(unittest.TestCase):
    def test_only_exact_three_fixed_messages_admitted(self):
        self.assertTrue(q.admitted_records(q.EVENTS))
        for bad in (
            list(q.EVENTS), q.EVENTS[:-1], tuple(reversed(q.EVENTS)),
            tuple({**q.EVENTS[i], "team_id": 303} if i == 0 else q.EVENTS[i] for i in range(3)),
            None, "", (),
        ):
            with self.subTest(bad=repr(bad)[:50]):
                self.assertFalse(q.admitted_records(bad))
        modified = list(deepcopy(q.EVENTS))
        modified[0]["properties"]["$pathname"] = "/hidden'; DROP TABLE x; --"
        self.assertFalse(q.admitted_records(tuple(modified)))

    def test_bounded_sql_and_rejected_index(self):
        for i in range(3):
            statement = q.insert_statement(i, q.EVENTS)
            self.assertTrue(statement.isascii())
            self.assertLessEqual(len(statement), 256)
            self.assertIn(f",{q.EVENTS[i]['team_id']},'user-one')", statement)
            self.assertIn("ENGINE=Memory", q.CREATE_SQL)
        for index in (-1, 3, True, False, 1.5, "1", None):
            with self.assertRaises(ValueError):
                q.insert_statement(index, q.EVENTS)

    @patch.object(q, "sql_http")
    def test_three_real_readback_queries_and_unconditional_drop(self, sql):
        sql.side_effect = [b"", b"", b"", b"", b"2\t1\t1\t1\n", b"1\t1\t1\t0\n", b"0\n", b"0\n", b""]
        result = q.relay_readback(18123, q.EVENTS)
        self.assertTrue(result["synthetic_relay_passed"])
        self.assertTrue(result["cross_team_path_reads_absent"])
        self.assertEqual(result["kafka_records_replayed"], 3)
        self.assertEqual(sql.call_count, 9)
        self.assertEqual(sql.call_args_list[-1].args[1], "DROP TABLE IF EXISTS flind_wave85_relay_events")
        queries = [call.args[1] for call in sql.call_args_list]
        self.assertEqual(sum("WHERE team_id=101" in x for x in queries), 2)
        self.assertEqual(sum("WHERE team_id=202" in x for x in queries), 2)

    @patch.object(q, "sql_http")
    def test_aggregate_mismatch_fails_and_drops(self, sql):
        sql.side_effect = [b"", b"", b"", b"", b"3\t1\t1\t1\n", b""]
        with self.assertRaisesRegex(ValueError, "aggregate mismatch"):
            q.relay_readback(18123, q.EVENTS)
        self.assertEqual(sql.call_args_list[-1].args[1], "DROP TABLE IF EXISTS flind_wave85_relay_events")

    @patch.object(q, "sql_http")
    def test_cross_team_path_leak_fails_and_drops(self, sql):
        sql.side_effect = [b"", b"", b"", b"", b"2\t1\t1\t1\n", b"1\t1\t1\t0\n", b"1\n", b""]
        with self.assertRaisesRegex(ValueError, "cross-team"):
            q.relay_readback(18123, q.EVENTS)
        self.assertEqual(sql.call_args_list[-1].args[1], "DROP TABLE IF EXISTS flind_wave85_relay_events")

    @patch.object(q, "sql_http")
    def test_partial_insert_failure_also_drops(self, sql):
        sql.side_effect = [b"", b"", ValueError("synthetic failure"), b""]
        with self.assertRaisesRegex(ValueError, "synthetic failure"):
            q.relay_readback(18123, q.EVENTS)
        self.assertEqual(sql.call_args_list[-1].args[1], "DROP TABLE IF EXISTS flind_wave85_relay_events")

    def test_no_sql_before_port_or_schema_or_event_validation(self):
        for port in (0, -1, 65536, True, None, "8123"):
            with patch.object(q, "sql_http") as sql:
                with self.assertRaises(ValueError):
                    q.relay_readback(port, q.EVENTS)
                sql.assert_not_called()
        with patch.object(q, "original_event_columns_present", return_value=False), patch.object(q, "sql_http") as sql:
            with self.assertRaises(ValueError):
                q.relay_readback(18123, q.EVENTS)
            sql.assert_not_called()

    @patch.object(q, "isolated_clickhouse")
    def test_callback_only_trusts_real_isolated_clickhouse_success(self, clickhouse):
        clickhouse.return_value = {"isolated_clickhouse_passed": False, "event_readback": {
            "synthetic_relay_passed": True, "cross_team_path_reads_absent": True,
            "kafka_records_replayed": 3,
        }}
        self.assertFalse(q._clickhouse_from_consumed(q.EVENTS)["synthetic_relay_passed"])
        clickhouse.return_value = {"isolated_clickhouse_passed": True, "event_readback": {
            "synthetic_relay_passed": True, "cross_team_path_reads_absent": True,
            "kafka_records_replayed": 3,
        }}
        report = q._clickhouse_from_consumed(q.EVENTS)
        self.assertTrue(report["synthetic_relay_passed"])
        self.assertEqual(report["kafka_records_replayed"], 3)

    @patch.object(q, "qualify_kafka")
    def test_joint_receipt_refuses_forgery_and_keeps_release_gates_false(self, kafka):
        home = Path("/fake-local-kafka")
        kafka.return_value = {"isolated_kafka_passed": False, "exact_json_message_roundtrip": True,
                              "synthetic_relay": {"synthetic_relay_passed": True,
                                                  "private_clickhouse_passed": True,
                                                  "kafka_records_replayed": 3}}
        self.assertFalse(q.qualify_joint_relay(home)["synthetic_kafka_cli_to_clickhouse_relay_qualified"])
        kafka.return_value["isolated_kafka_passed"] = True
        report = q.qualify_joint_relay(home)
        self.assertTrue(report["synthetic_kafka_cli_to_clickhouse_relay_qualified"])
        self.assertEqual(report["synthetic_messages_replayed"], 3)
        for flag in (
            "sdk_ingestion_qualified", "flind_production_ingester_qualified",
            "production_kafka_to_clickhouse_qualified", "production_events_schema_qualified",
            "dashboard_query_qualified", "tenant_authorization_qualified", "release_qualified",
        ):
            self.assertIs(report[flag], False)
        kafka.assert_called_with(home, on_consumed=q._clickhouse_from_consumed)


if __name__ == "__main__":
    unittest.main()
