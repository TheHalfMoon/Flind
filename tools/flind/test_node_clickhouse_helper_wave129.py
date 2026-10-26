"""Wave129: actual first-party Node ClickHouse class ↔ real private ClickHouse."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import bootstrap_native_re2_node24_wave129 as native
from tools.flind import qualify_node_clickhouse_helper_wave129 as q


class NativeClickhouseHelperWave129(unittest.TestCase):
    def test_real_first_party_helper_sql_query_via_jest(self):
        if not (q.NODE24 / "node").is_file() or not q.BINARY.is_file():
            self.skipTest("Preinstalled Node24 and supported CH25.12 required")
        receipt = q.qualify()
        self.assertTrue(receipt["first_party_node24_clickhouse_helper_real_sql_qualified"],
                        receipt.get("blocker"))
        self.assertTrue(receipt["isolated_real_clickhouse_started"])
        actual = receipt["real_original_helper_receipt"]
        self.assertTrue(actual["actual_first_party_clickhouse_helper_jest_passed"])
        self.assertTrue(actual["scratch_source_restored"])
        self.assertEqual(actual["native_jest_exit_code"], 0)
        self.assertFalse(receipt["production_rust_node_clickhouse_ingestion_qualified"])
        self.assertFalse(receipt["release_qualified"])

    def test_pinned_re2_native_binding_is_importable_with_node24(self):
        state = native.qualify()
        self.assertTrue(state["node24_local_native_re2_qualified"], state.get("blocker"))
        self.assertEqual(state["pinned_native_dependency"], "re2@1.22.1")
        self.assertFalse(state["node24_global_switch"])
        self.assertFalse(state["paid_cloud_used"])
        self.assertFalse(state["release_qualified"])

    def test_missing_binary_fails_before_private_database_or_jest(self):
        with patch.object(q, "BINARY", Path("/nonexistent/owned-clickhouse")):
            receipt = q.qualify()
        self.assertFalse(receipt["first_party_node24_clickhouse_helper_real_sql_qualified"])
        self.assertFalse(receipt["release_qualified"])

    def test_no_original_clickhouse_helper_test_is_a_mock(self):
        test = (q.ROOT / q.FILES[2]).read_text()
        self.assertIn("import { Clickhouse } from './clickhouse'", test)
        self.assertIn("Clickhouse.create()", test)
        self.assertIn("client.query", test)
        self.assertIn("currentDatabase()", test)
        self.assertIn("flind_private_probe", test)
        self.assertNotIn("jest.mock", test)

    def test_native_re2_build_is_offline_and_bounded(self):
        source = (q.ROOT / "tools/flind/bootstrap_native_re2_node24_wave129.py").read_text()
        self.assertIn("nodedir=", source)
        self.assertIn("node24_local_native_re2_qualified", source)
        self.assertIn("CPLUS_INCLUDE_PATH", source)
        self.assertIn("C_INCLUDE_PATH", source)
        self.assertIn("os.killpg", source)
        self.assertIn("MIN_FREE", source)
        self.assertNotIn("pnpm install", source)
        self.assertNotIn("brew install", source)


if __name__ == "__main__":
    unittest.main()
