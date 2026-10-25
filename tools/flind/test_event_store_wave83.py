"""Wave 83: synthetic real ClickHouse event-store readback guardrails."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tools.flind import qualify_event_store_wave83 as e
from tools.flind import qualify_ephemeral_clickhouse as ch


class EventStoreWave83Tests(unittest.TestCase):
    def test_matches_actual_flind_event_template_not_a_guessed_name(self):
        self.assertTrue(e.original_event_columns_present())
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "posthog" / "models" / "event"
            path.mkdir(parents=True)
            original = (e.ROOT / "posthog/models/event/sql.py").read_text()
            (path / "sql.py").write_text(original.replace("team_id Int64,", "team_id String,", 1))
            self.assertFalse(e.original_event_columns_present(Path(tmp)))

    def test_test_table_is_disposable_and_uses_exact_canonical_columns(self):
        self.assertIn("ENGINE=Memory", e.CREATE_SQL)
        self.assertIn("team_id Int64", e.CREATE_SQL)
        self.assertIn("uuid UUID", e.CREATE_SQL)
        self.assertIn("timestamp DateTime64(6,'UTC')", e.CREATE_SQL)
        self.assertNotIn("ON CLUSTER", e.CREATE_SQL)

    def test_team_id_guards_refuse_boolean_negative_overflow_and_injections(self):
        for bad in (True, False, None, "101", "101 OR 1=1", 0, -1, 2**63, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    e.team_scoped_summary_sql(bad)
        self.assertTrue(e.team_scoped_summary_sql(202).endswith("WHERE team_id=202"))

    def test_synthetic_fixture_sql_is_bounded_ascii_and_cannot_be_injected(self):
        self.assertEqual(len(e.EVENTS), 6)
        self.assertEqual({x[0] for x in e.EVENTS}, {101, 202})
        self.assertEqual(
            {x[1] for x in e.EVENTS if x[0] == 101}
            & {x[1] for x in e.EVENTS if x[0] == 202},
            {"user-one"},
        )
        for i in range(len(e.EVENTS)):
            query = e.synthetic_insert_sql(i)
            self.assertTrue(query.isascii())
            self.assertLessEqual(len(query), 256)
            self.assertIn("INSERT INTO flind_wave83_events", query)
        for bad in (True, -1, len(e.EVENTS), None, "1"):
            with self.assertRaises(ValueError):
                e.synthetic_insert_sql(bad)

    @patch.object(e, "sql_http")
    def test_full_roundtrip_contract_and_unconditional_drop(self, sql):
        # SQL responses for CREATE, 6 INSERTs, scoped teams, cross-team paths
        # and final DROP. No real connection in this test.
        sql.side_effect = [
            b"", *(b"" for _ in e.EVENTS),
            b"4\t2\t2\t1\n", b"2\t2\t2\t0\n", b"0\n", b"0\n", b"",
        ]
        report = e.event_roundtrip(18399)
        self.assertTrue(report["real_clickhouse_insert_select_passed"])
        self.assertFalse(report["release_qualified"])
        self.assertFalse(report["sdk_ingestion_qualified"])
        self.assertEqual(report["synthetic_events_inserted"], 6)
        calls = [call.args[1] for call in sql.call_args_list]
        self.assertEqual(len(calls), 12)
        self.assertTrue(calls[0].startswith("CREATE TABLE"))
        self.assertEqual(sum("WHERE team_id=101" in q for q in calls), 2)
        self.assertEqual(sum("WHERE team_id=202" in q for q in calls), 2)
        self.assertEqual(calls[-1], "DROP TABLE IF EXISTS flind_wave83_events")

    @patch.object(e, "sql_http")
    def test_cross_team_path_leak_fails_and_drops_table(self, sql):
        sql.side_effect = [
            b"", *(b"" for _ in e.EVENTS),
            b"4\t2\t2\t1\n", b"2\t2\t2\t0\n", b"1\n", b"0\n", b"",
        ]
        with self.assertRaisesRegex(ValueError, "leaked"):
            e.event_roundtrip(18399)
        self.assertEqual(sql.call_args_list[-1].args[1], "DROP TABLE IF EXISTS flind_wave83_events")

    @patch.object(e, "sql_http")
    def test_partial_insert_failure_also_drops_private_table(self, sql):
        sql.side_effect = [b"", b"", ValueError("test insert failed"), b""]
        with self.assertRaisesRegex(ValueError, "insert failed"):
            e.event_roundtrip(18399)
        self.assertEqual(sql.call_args_list[-1].args[1], "DROP TABLE IF EXISTS flind_wave83_events")

    def test_http_port_guard(self):
        for value in (True, None, 0, -1, 65536, "8123"):
            with self.assertRaises(ValueError):
                e.event_roundtrip(value)

    @patch.object(ch, "pick_loopback_port", return_value=18123)
    @patch.object(ch, "clickhouse_ping", return_value=SimpleNamespace(ready=True))
    @patch.object(ch, "query_roundtrip", return_value={"rows": 3, "sum": 60})
    @patch.object(ch, "qualify", return_value={"release_qualified": False})
    @patch.object(ch, "local_service_versions", return_value={})
    @patch.object(ch.subprocess, "Popen")
    def test_private_service_calls_event_probe_and_terminates_even_on_probe_failure(
        self, popen, _versions, _qualify, _baseline, _ping, _port
    ):
        child = MagicMock()
        child.poll.return_value = None
        popen.return_value = child
        observed = []
        receipt = ch.isolated_clickhouse(
            binary="/tmp/not-run-in-mock",
            on_ready=lambda port: observed.append(port) or {"actual_test_probe": True},
        )
        self.assertTrue(receipt["isolated_clickhouse_passed"])
        self.assertEqual(receipt["event_readback"], {"actual_test_probe": True})
        self.assertEqual(observed, [18123])
        child.terminate.assert_called_once()
        child.wait.assert_called_once()

        child.reset_mock()
        bad = ch.isolated_clickhouse(
            binary="/tmp/not-run-in-mock",
            on_ready=lambda port: (_ for _ in ()).throw(ValueError("synthetic failure")),
        )
        self.assertFalse(bad["isolated_clickhouse_passed"])
        self.assertFalse(bad["release_qualified"])
        child.terminate.assert_called_once()
        child.wait.assert_called_once()

    @patch.object(e, "isolated_clickhouse")
    def test_forged_receipt_cannot_be_qualified(self, isolated):
        isolated.return_value = {
            "isolated_clickhouse_passed": False,
            "event_readback": {
                "canonical_flind_event_fields_matched": True,
                "real_clickhouse_insert_select_passed": True,
                "cross_team_path_readback_absent": True,
            },
        }
        result = e.qualify_event_store()
        self.assertFalse(result["real_flind_shaped_event_readback_qualified"])
        self.assertFalse(result["release_qualified"])
        isolated.assert_called_once()

    @patch.object(e, "isolated_clickhouse")
    def test_success_receipt_never_promotes_full_sdk_or_dashboard(self, isolated):
        isolated.return_value = {
            "isolated_clickhouse_passed": True,
            "event_readback": {
                "canonical_flind_event_fields_matched": True,
                "real_clickhouse_insert_select_passed": True,
                "cross_team_path_readback_absent": True,
            },
        }
        result = e.qualify_event_store()
        self.assertTrue(result["real_flind_shaped_event_readback_qualified"])
        for gate in ("release_qualified", "sdk_ingestion_qualified", "kafka_ingestion_qualified", "dashboard_query_qualified"):
            self.assertFalse(result[gate])


if __name__ == "__main__":
    unittest.main()
