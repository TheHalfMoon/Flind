"""Wave125 repeatable original first-party Node WorkerIngest Jest qualification."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_node_ingestion_jest_wave125 as q


class NodeOriginalJestWave125(unittest.TestCase):
    def test_real_original_jest_suites_pass_in_frozen_local_node_workspace(self):
        if not (q.FULL / "nodejs/node_modules/.bin/jest").is_file():
            self.skipTest("Free locked Node modules not installed")
        receipt = q.qualify()
        self.assertTrue(receipt["original_node_jest_all_four_suites_qualified"], receipt.get("blocker"))
        self.assertEqual(receipt["original_jest_suite_count"], 4)
        self.assertGreaterEqual(receipt["original_jest_test_count"], 43)
        self.assertTrue(receipt["temporary_checkout_sources_restored"])
        self.assertEqual(receipt["native_jest_process_exit"], 0)
        for field in (
            "production_node_ingestion_worker_started",
            "production_clickhouse_persistence_qualified",
            "tenant_authenticated_api_qualified",
            "browser_dashboard_e2e_qualified",
            "release_qualified",
        ):
            self.assertFalse(receipt[field])

    def test_must_be_exact_original_node_product_jest_paths(self):
        self.assertEqual(q.TESTS, (
            "src/ingestion/api/kafka-message-converter.test.ts",
            "src/ingestion/api/grpc-message-converter.test.ts",
            "src/ingestion/api/grpc-server.test.ts",
            "src/servers/grpc-stream-ingest-driver.test.ts",
        ))

    def test_all_current_main_product_files_are_overlaid(self):
        self.assertIn("nodejs/src/ingestion/api/grpc-server.ts", q.OVERLAY)
        self.assertIn("nodejs/src/ingestion/api/grpc-message-converter.ts", q.OVERLAY)
        self.assertIn("nodejs/src/ingestion/api/kafka-message-converter.ts", q.OVERLAY)
        self.assertIn("nodejs/src/servers/grpc-stream-ingest-driver.ts", q.OVERLAY)
        for relative in q.OVERLAY:
            self.assertTrue((q.ROOT / relative).is_file(), relative)

    def test_missing_frozen_node_modules_refused_before_execution(self):
        with patch.object(q, "FULL", Path("/nonexistent/flind-scratch-checkout")):
            result = q.qualify()
        self.assertFalse(result["original_node_jest_all_four_suites_qualified"])
        self.assertFalse(result["release_qualified"])
        self.assertIn("blocker", result)

    def test_only_local_jest_and_no_install_or_publish(self):
        source = (q.ROOT / "tools/flind/qualify_node_ingestion_jest_wave125.py").read_text()
        self.assertIn('"./node_modules/.bin/jest"', source)
        self.assertIn('"--runInBand"', source)
        self.assertIn('"--runTestsByPath"', source)
        self.assertIn('subprocess.Popen', source)
        self.assertIn('start_new_session=True', source)
        self.assertIn('old.items()', source)
        self.assertIn('shutil.disk_usage("/tmp").free < MIN_FREE', source)
        # The docstring mentions installation as a negative. Reject actual
        # subprocess argv entries, not commentary documenting that boundary.
        self.assertNotIn('"npm",', source)
        self.assertNotIn('"pnpm",', source)


if __name__ == "__main__":
    unittest.main()
