"""Wave186 guard tests: original source, explicit scratch, real HTTP2 receipt."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_actual_node_grpc_http2_wire_wave186 as w


PASS = {
    "assertions_passed": 20,
    "actual_first_party_grpc_server_started": True,
    "real_grpc_http2_handshake_and_ack": True,
    "unsafe_sequence_rejected": True,
    "first_party_node_worker_pipeline_qualified": False,
    "first_party_rust_to_node_qualified": False,
    "durable_clickhouse_qualified": False,
    "authenticated_tenant_isolation_qualified": False,
    "release_qualified": False,
}


class NodeGrpcWireAdmissionTests(unittest.TestCase):
    def test_exact_original_source_whitelist(self):
        self.assertEqual(len(w.SRC), 8)
        self.assertEqual(len(w.VERSIONS), 5)
        self.assertEqual(w.VERSIONS["@connectrpc/connect-node"], "2.1.1")
        self.assertEqual(w.VERSIONS["@bufbuild/protobuf"], "2.11.0")
        self.assertEqual(w.COUNT, 20)

    def test_exact_success_receipt(self):
        self.assertTrue(w.receipt_ok(PASS))
        self.assertFalse(w.receipt_ok(None))
        self.assertFalse(w.receipt_ok([]))

    def test_forged_or_missing_assertions_denied(self):
        self.assertFalse(w.receipt_ok({**PASS, "assertions_passed": 19}))
        self.assertFalse(w.receipt_ok({**PASS, "assertions_passed": 20.0, "real_grpc_http2_handshake_and_ack": False}))
        self.assertFalse(w.receipt_ok({**PASS, "real_grpc_http2_handshake_and_ack": None}))

    def test_never_promote_prod_worker_auth_or_release(self):
        for name in (
            "first_party_node_worker_pipeline_qualified",
            "first_party_rust_to_node_qualified",
            "durable_clickhouse_qualified",
            "authenticated_tenant_isolation_qualified",
            "release_qualified",
        ):
            self.assertFalse(w.receipt_ok({**PASS, name: True}), name)

    def test_unowned_temp_directory_refuses_to_run(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave186-unowned-", dir="/private/tmp") as root:
            folder = Path(root)
            with self.assertRaises(w.Denied):
                w.admitted(Path("/private/tmp/flind-wave171-current-boot"), folder,
                           Path("/private/tmp/flind-wave164-runner"))

    def test_marker_mismatch_refuses_to_run(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave186-unowned-", dir="/private/tmp") as root:
            folder = Path(root)
            (folder / w.MARKER).write_text("WRONG\n")
            with self.assertRaisesRegex(w.Denied, "unowned_node_grpc_scratch"):
                w.admitted(Path("/private/tmp/flind-wave171-current-boot"), folder,
                           Path("/private/tmp/flind-wave164-runner"))

    def test_missing_real_deps_or_unpatched_http2_refused(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave186-unit-", dir="/private/tmp") as root:
            folder = Path(root)
            with self.assertRaisesRegex(w.Denied, "missing_pinned_real_grpc_dependency"):
                w.checked_dependencies(folder)
            for name, version in w.VERSIONS.items():
                manifest = folder / "node_modules" / name / "package.json"
                manifest.parent.mkdir(parents=True, exist_ok=True)
                manifest.write_text('{"version":"' + version + '"}')
            with self.assertRaisesRegex(w.Denied, "missing_first_party_connect_http2_patch"):
                w.checked_dependencies(folder)

    def test_modified_original_git_source_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave186-unit-", dir="/private/tmp") as root:
            folder = Path(root)
            (folder / w.MARKER).write_text(w.MARKER_VALUE)
            with patch.object(w, "original_blob", side_effect=w.Denied("source_drift")), patch.object(
                w, "checked_dependencies"
            ):
                receipt = w.run(Path("/private/tmp/flind-wave171-current-boot"), folder,
                                Path("/private/tmp/flind-wave164-runner"))
            self.assertFalse(receipt["real_first_party_http2_grpc_worker_server_qualified"])
            self.assertFalse(receipt["release_qualified"])
            self.assertEqual(receipt["blocker"], "source_drift")

    def test_actual_original_node_http2_grpc_wire_on_mac_scratch(self):
        reference = Path("/private/tmp/flind-wave171-current-boot")
        scratch = Path("/private/tmp/flind-wave186-grpc-core")
        scriptroot = Path("/private/tmp/flind-wave164-runner")
        if not all(path.is_dir() for path in (reference, scratch, scriptroot)):
            self.skipTest("Scoped local Mac scratch resources not available")
        receipt = w.run(reference, scratch, scriptroot)
        self.assertTrue(receipt["real_first_party_http2_grpc_worker_server_qualified"], receipt)
        self.assertEqual(receipt["synthetic_wire_assertions_passed"], 20)
        self.assertFalse(receipt["production_ingestion_driver_qualified"])
        self.assertFalse(receipt["authenticated_tenant_isolation_qualified"])
        self.assertFalse(receipt["release_qualified"])


if __name__ == "__main__":
    unittest.main()
