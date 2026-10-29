"""Fail-closed, source-compatible regression tests for real Kafka ENGINE probe.

All service interactions are mocked; live qualification must additionally be
run with the exact original owner-only Kafka and supported ClickHouse assets.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_kafka_engine_wave255 as q


class RealKafkaEngineWave255Tests(unittest.TestCase):
    def test_original_fixture_is_cross_team_collision(self):
        rows = q.fixture()
        self.assertEqual([r["team_id"] for r in rows], [101, 202, 101])
        self.assertEqual(len({r["uuid"] for r in rows}), 3)
        self.assertEqual(len({r["distinct_id"] for r in rows}), 1)
        self.assertEqual(len({r["token"] for r in rows}), 1)

    def test_original_fixture_tampering_fails_closed(self):
        with patch.object(q, "EVENTS", ({"team_id": 101, "distinct_id": "wrong"},)):
            with self.assertRaises(q.Refused):
                q.fixture()

    def test_low_disk_rejected_before_original_kafka_launch(self):
        with patch.object(q, "admit", side_effect=q.Refused("disk reserve")), patch.object(
            q, "qualify_kafka"
        ) as kafka:
            result = q.qualify(Path("/missing"), Path("/missing"), Path("/missing"))
        kafka.assert_not_called()
        self.assertFalse(result["actual_clickhouse_kafka_engine_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_disk_floor_has_strict_fail_closed_boundary(self):
        with patch.object(q.shutil, "disk_usage", return_value=SimpleNamespace(
            free=q.FREE_FLOOR_BYTES - 1
        )):
            with self.assertRaisesRegex(q.Refused, "disk_reserve"):
                q.require_space(q.FREE_FLOOR_BYTES)

    def test_non_loopback_broker_is_rejected_without_database_interaction(self):
        with patch.object(q, "sql") as sql:
            with self.assertRaisesRegex(q.Refused, "non_loopback"):
                q.engine_readback(18000, "broker.example.com:9092", q.fixture())
        sql.assert_not_called()

    def test_sql_helper_rejects_unsafe_inputs_before_http_connection(self):
        with patch.object(q, "HTTPConnection") as connection:
            for port, statement in [
                (True, "SELECT 1"),
                (3, "SELECT 1"),
                (18000, "x" * 1801),
                (18000, "SELECT 'é'"),
            ]:
                with self.subTest(port=port):
                    with self.assertRaises(q.Refused):
                        q.sql(port, statement)
        connection.assert_not_called()

    def _engine_results(self, *, records=None, team_counts="101\t2\n202\t1",
                        disk_parts="1\t3"):
        rows = sorted(records if records is not None else q.fixture(),
                      key=lambda x: x["uuid"])
        return [
            q.EXPECTED_VERSION, "Kafka", "MergeTree", "", "", "",
            "\n".join(json.dumps(x) for x in rows),
            team_counts, "0", disk_parts, "", "", "",
        ]

    def test_real_kafka_engine_sql_plan_and_readback_mock(self):
        with patch.object(q, "require_space"), patch.object(q, "sql", side_effect=self._engine_results()) as sql:
            receipt = q.engine_readback(18000, "127.0.0.1:19092", q.fixture())
        self.assertTrue(receipt["real_clickhouse_kafka_engine_subscription_qualified"])
        self.assertTrue(receipt["real_materialized_view_mergetree_rows_qualified"])
        self.assertTrue(receipt["disk_parts_on_actual_mergetree_verified"])
        self.assertEqual(receipt["three_synthetic_rows_exact"], 3)
        self.assertFalse(receipt["production_native_rust_ingest_qualified"])
        self.assertFalse(receipt["production_node_ingest_qualified"])
        self.assertFalse(receipt["authenticated_tenant_authorization_qualified"])
        self.assertFalse(receipt["release_qualified"])
        statements = [x.args[1] for x in sql.call_args_list]
        self.assertTrue(any("ENGINE=Kafka" in x for x in statements))
        self.assertTrue(any("CREATE MATERIALIZED VIEW" in x for x in statements))
        self.assertTrue(any("ENGINE=MergeTree" in x for x in statements))
        self.assertTrue(any("FROM system.parts" in x for x in statements))
        self.assertEqual([x for x in statements if x.startswith("DROP ")],
                         [f"DROP VIEW IF EXISTS {q.VIEW}",
                          f"DROP TABLE IF EXISTS {q.SOURCE}",
                          f"DROP TABLE IF EXISTS {q.TARGET}"])

    def test_cross_team_row_drift_never_passes_even_when_count_is_three(self):
        rows = q.fixture()
        rows[0]["team_id"] = 202
        with patch.object(q, "require_space"), patch.object(q, "sql", side_effect=self._engine_results(records=rows)) as sql:
            with self.assertRaisesRegex(q.Refused, "readback_mismatch"):
                q.engine_readback(18000, "127.0.0.1:19092", q.fixture())
        self.assertEqual(sum(x.args[1].startswith("DROP ") for x in sql.call_args_list), 3)

    def test_no_disk_parts_never_passes_durable_gate(self):
        with patch.object(q, "require_space"), patch.object(q, "sql", side_effect=self._engine_results(disk_parts="0\t0")):
            with self.assertRaisesRegex(q.Refused, "disk_parts_missing"):
                q.engine_readback(18000, "127.0.0.1:19092", q.fixture())

    def test_wrong_count_never_passes_cross_team_gate(self):
        with patch.object(q, "require_space"), patch.object(q, "sql", side_effect=self._engine_results(team_counts="101\t1\n202\t2")):
            with self.assertRaisesRegex(q.Refused, "team_filter_mismatch"):
                q.engine_readback(18000, "127.0.0.1:19092", q.fixture())

    def test_fake_official_asset_is_rejected_before_any_service(self):
        with TemporaryDirectory(dir="/private/tmp", prefix="flind-wave255-unit-") as td:
            base = Path(td)
            owner = base / "owner"
            owner.mkdir()
            (owner / ".flind-owner-only").write_text(q.ASSET_OWNER)
            asset = owner / "clickhouse"
            asset.write_bytes(b"wrong binary")
            repo = base / "repo"
            repo.mkdir()
            kafka = base / "kafka"
            (kafka / "bin").mkdir(parents=True)
            (kafka / "bin/kafka-server-start.sh").write_text("test fixture")
            with patch.object(q, "require_space"):
                with self.assertRaisesRegex(q.Refused, "unapproved_clickhouse_asset_path"):
                    q.admit(repo, kafka, asset)

    def test_owner_marker_is_required_even_if_asset_size_matches(self):
        with TemporaryDirectory(dir="/private/tmp", prefix="flind-wave255-unit-") as td:
            base = Path(td)
            owner = base / "owner"
            owner.mkdir()
            asset = owner / "clickhouse"
            asset.write_bytes(b"short")
            repo = base / "repo"
            repo.mkdir()
            kafka = base / "kafka"
            (kafka / "bin").mkdir(parents=True)
            (kafka / "bin/kafka-server-start.sh").write_text("test fixture")
            with patch.object(q, "ROOT", base), patch.object(q, "ASSET_SIZE", 5), patch.object(
                q, "require_space"
            ):
                with self.assertRaisesRegex(q.Refused, "unowned_official_clickhouse_asset"):
                    q.admit(repo, kafka, asset)

    def test_original_kafka_qualifier_receipt_does_not_promote_prod(self):
        with TemporaryDirectory(dir="/private/tmp", prefix="flind-wave255-unit-") as td:
            base = Path(td)
            owner = base / "owner"
            owner.mkdir()
            (owner / ".flind-owner-only").write_text(q.ASSET_OWNER)
            asset = owner / "clickhouse"
            asset.write_bytes(b"fixture")
            with patch.object(q, "admit", return_value="a" * 40), patch.object(
                q, "ROOT", base
            ), patch.object(q.shutil, "copyfile", side_effect=lambda src,dst: Path(dst).write_bytes(b"fixture")), patch.object(q, "qualify_kafka",
                       return_value={"isolated_kafka_passed": True,
                                     "exact_json_message_roundtrip": True,
                                     "native_capture_relay": {
                                         "actual_clickhouse_kafka_engine_qualified": True,
                                         "detail": {"real_clickhouse_kafka_engine_subscription_qualified": True}
                                     }}):
                result = q.qualify(base, base, asset)
        self.assertTrue(result["actual_clickhouse_kafka_engine_qualified"])
        for field in ("original_rust_production_worker_qualified",
                      "original_node_production_ingest_qualified",
                      "authenticated_tenant_qualified",
                      "distributed_clickhouse_migrations_qualified",
                      "release_qualified"):
            self.assertFalse(result[field])


if __name__ == "__main__":
    unittest.main()
