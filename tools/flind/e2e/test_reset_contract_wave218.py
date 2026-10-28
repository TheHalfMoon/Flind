"""Wave218 first-party schema contract and safety regressions; never invoke Docker."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.flind.e2e import schema_preflight_wave216 as gate


class Wave218OriginalSchemaGateTests(unittest.TestCase):
    def test_exact_first_party_reset_source_contract(self):
        self.assertTrue(gate.validate_original_reset_contract())
        self.assertEqual(len(gate.POSTGRES_REQUIRED), 8)
        self.assertEqual(len(gate.PERSONS_REQUIRED), 10)
        self.assertEqual(len(gate.CLICKHOUSE_REQUIRED), 13)

    def test_upstream_postgres_reset_addition_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "sql.ts"
            original = gate.SQL_HELPER.read_text()
            source.write_text(original.replace(
                "DELETE FROM posthog_cohort CASCADE;",
                "DELETE FROM posthog_extra CASCADE;\n    DELETE FROM posthog_cohort CASCADE;",
                1,
            ))
            with patch.object(gate, "SQL_HELPER", source):
                with self.assertRaisesRegex(ValueError, "contract changed"):
                    gate.validate_original_reset_contract()

    def test_upstream_clickhouse_reset_addition_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "clickhouse.ts"
            original = gate.CH_HELPER.read_text()
            source.write_text(original.replace(
                "this.truncate('sharded_events'),",
                "this.truncate('extra_table'),\n            this.truncate('sharded_events'),",
                1,
            ))
            with patch.object(gate, "CH_HELPER", source):
                with self.assertRaisesRegex(ValueError, "contract changed"):
                    gate.validate_original_reset_contract()

    def test_absent_source_refuses_before_db(self):
        with patch.object(gate, "SQL_HELPER", Path("/nonexistent/sql.ts")):
            with patch.object(gate, "inspect", side_effect=AssertionError("DB accessed")):
                with self.assertRaisesRegex(ValueError, "source unavailable"):
                    gate.preflight()

    def test_nonowned_postgres_database_refused(self):
        with patch.object(gate.subprocess, "run", side_effect=AssertionError("Docker launched")):
            with self.assertRaisesRegex(ValueError, "non-owned"):
                gate.postgres_tables("zyara")

    def test_full_reset_preconditions_do_not_claim_release(self):
        common = set(gate.POSTGRES_REQUIRED) | {"django_migrations"}
        with patch.object(gate, "inspect", return_value={}), \
             patch.object(gate, "assert_owned_service"), \
             patch.object(gate, "read_database_names"), \
             patch.object(gate, "check_redis"), \
             patch.object(gate, "check_clickhouse"), \
             patch.object(gate, "postgres_tables", side_effect=[common, set(gate.PERSONS_REQUIRED)]), \
             patch.object(gate, "clickhouse_tables", return_value=set(gate.CLICKHOUSE_REQUIRED)), \
             patch.object(gate, "postgres_migration_count", return_value=839), \
             patch.object(gate, "clickhouse_kafka_engine_count", return_value=2):
            result = gate.preflight()
        self.assertTrue(result["schema_preconditions_passed"])
        self.assertFalse(result["full_migration_graph_qualified"])
        self.assertFalse(result["original_node_service_e2e_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_persons_schema_absent_blocks_even_with_common_tables(self):
        common = set(gate.POSTGRES_REQUIRED) | {"django_migrations"}
        with patch.object(gate, "inspect", return_value={}), \
             patch.object(gate, "assert_owned_service"), \
             patch.object(gate, "read_database_names"), \
             patch.object(gate, "check_redis"), \
             patch.object(gate, "check_clickhouse"), \
             patch.object(gate, "postgres_tables", side_effect=[common, set()]), \
             patch.object(gate, "clickhouse_tables", return_value=set(gate.CLICKHOUSE_REQUIRED)), \
             patch.object(gate, "postgres_migration_count", return_value=1), \
             patch.object(gate, "clickhouse_kafka_engine_count", return_value=1):
            result = gate.preflight()
        self.assertEqual(len(result["missing_persons_tables"]), 10)
        self.assertFalse(result["original_postgres_schema_ready"])

    def test_missing_ledger_and_kafka_engine_blocks(self):
        with patch.object(gate, "inspect", return_value={}), \
             patch.object(gate, "assert_owned_service"), \
             patch.object(gate, "read_database_names"), \
             patch.object(gate, "check_redis"), \
             patch.object(gate, "check_clickhouse"), \
             patch.object(gate, "postgres_tables", side_effect=[set(gate.POSTGRES_REQUIRED), set(gate.PERSONS_REQUIRED)]), \
             patch.object(gate, "clickhouse_tables", return_value=set(gate.CLICKHOUSE_REQUIRED)), \
             patch.object(gate, "postgres_migration_count", side_effect=AssertionError("queried nonexistent table")), \
             patch.object(gate, "clickhouse_kafka_engine_count", return_value=0):
            result = gate.preflight()
        self.assertFalse(result["common_django_migration_rows_present"])
        self.assertFalse(result["clickhouse_kafka_engine_present"])
        self.assertFalse(result["schema_preconditions_passed"])


if __name__ == "__main__":
    unittest.main()
