"""Wave185: fail-closed Git source checks and Node runtime receipt admission."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_original_node_grpc_primitives_wave185 as wave

YES = {
    "tests_passed": 32,
    "original_grpc_int64_precision_pass": True,
    "original_kafka_message_conversion_pass": True,
    "original_grpc_error_sanitization_pass": True,
    "external_modules_used": False,
    "production_grpc_server_qualified": False,
    "production_node_grpc_server_qualified": False,
    "production_node_worker_qualified": False,
    "real_rust_to_production_node_qualified": False,
    "durable_clickhouse_qualified": False,
    "authenticated_tenant_isolation_qualified": False,
    "release_qualified": False,
}


class OfflineNodeBoundaryAdmission(unittest.TestCase):
    def test_original_git_source_modules_are_immutable(self):
        self.assertEqual(len(wave.MODULES), 3)
        self.assertTrue(all(x.startswith("nodejs/src/ingestion/api/") for x in wave.MODULES))
        self.assertEqual(wave.RUNNER, "tools/flind/verify_original_grpc_boundary_wave185.mjs")

    def test_precise_count_and_all_qualified_primitive_flags(self):
        self.assertEqual(wave.TEST_COUNT, 32)
        self.assertTrue(wave._receipt_ok(YES))

    def test_insufficient_count_fail_closed(self):
        self.assertFalse(wave._receipt_ok({**YES, "tests_passed": 31}))
        self.assertFalse(wave._receipt_ok({**YES, "tests_passed": True}))
        self.assertFalse(wave._receipt_ok({"tests_passed": 32}))

    def test_forged_prod_release_or_worker_flags_refused(self):
        for name in ("production_node_grpc_server_qualified", "production_node_worker_qualified",
                     "real_rust_to_production_node_qualified", "release_qualified",
                     "authenticated_tenant_isolation_qualified"):
            self.assertFalse(wave._receipt_ok({**YES, name: True}))

    def test_missing_or_unsafe_source_never_runs_node(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave185-", dir="/private/tmp") as root:
            path = Path(root)
            with patch.object(wave.subprocess, "run") as process:
                receipt = wave.qualify(path, path)
            process.assert_not_called()
        self.assertFalse(receipt["original_node_grpc_kafka_primitives_pass"])
        self.assertFalse(receipt["release_qualified"])
        self.assertEqual(receipt["blocker"], "unavailable_or_symlinked_original_node_module")

    def test_git_mismatched_source_refused(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave185-", dir="/private/tmp") as root:
            path = Path(root)
            for module in wave.MODULES:
                filename = path / module
                filename.parent.mkdir(parents=True, exist_ok=True)
                filename.write_text("different")
            with patch.object(wave, "_blob", return_value=("a" * 40, b"original")), patch.object(
                wave.subprocess, "run"
            ) as process:
                receipt = wave.qualify(path, path)
            process.assert_not_called()
            self.assertEqual(receipt["blocker"], "original_node_source_drift")

    def test_unavailable_node_binary_cannot_promote_success(self):
        with patch.object(wave, "verified_modules", return_value={
            p: "a" * 40 for p in wave.MODULES
        }), patch.object(wave.shutil, "which", return_value=None), patch.object(
            wave.subprocess, "run"
        ) as run:
            result = wave.qualify(Path("/fake"), Path("/fake"))
        run.assert_not_called()
        self.assertFalse(result["original_node_grpc_kafka_primitives_pass"])
        self.assertEqual(result["blocker"], "unavailable_approved_node_binary")

    def test_real_original_node_regression_in_cached_local_environment(self):
        reference = Path("/private/tmp/flind-wave171-current-boot")
        candidate = Path("/private/tmp/flind-wave164-runner")
        if not reference.is_dir() or not candidate.is_dir():
            self.skipTest("Scoped local Mac fixtures not installed")
        result = wave.qualify(reference, candidate)
        self.assertTrue(result["git_attested_original_node_modules"])
        self.assertTrue(result["original_node_grpc_kafka_primitives_pass"])
        self.assertEqual(result["original_node_subtests_passed"], 32)
        self.assertFalse(result["production_node_grpc_server_qualified"])
        self.assertFalse(result["release_qualified"])


if __name__ == "__main__":
    unittest.main()
