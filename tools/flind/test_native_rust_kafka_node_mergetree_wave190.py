"""Fail-closed Wave190 native Kafka/Rust/Node durable test receipts and source admission."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.flind import qualify_native_rust_kafka_node_mergetree_wave190 as w

NATIVE = {
    "native_kafka_three_events": True,
    "original_rust_proto_node_http2_ack_three": True,
    "native_rust_committed_offset": 3,
    "production_rust_consumer_qualified": False,
    "production_node_pipeline_qualified": False,
    "release_qualified": False,
}
NODE = {
    "phase": "wave190_stopped",
    "durable_three_reopened": True,
    "accepted_batches": 1,
}

class NativeRustNodeDurabilityGuards(unittest.TestCase):
    def test_native_requires_all_actual_proof_fields(self):
        self.assertTrue(w.approved_native_receipt(NATIVE))
        self.assertFalse(w.approved_native_receipt(None))
        self.assertFalse(w.approved_native_receipt({}))

    def test_missing_or_forged_rust_ack_refused(self):
        for key in w.APPROVED_KEYS:
            for invalid in (False, None, 1, "true"):
                self.assertFalse(w.approved_native_receipt({**NATIVE, key:invalid}))

    def test_wrong_offset_or_type_never_promoted(self):
        for invalid in (0, 2, 4, True, 3.0, "3", None, -1):
            self.assertFalse(w.approved_native_receipt({
                **NATIVE, "native_rust_committed_offset":invalid,
            }))

    def test_native_product_and_release_claims_must_remain_false(self):
        for key in w.FORBIDDEN:
            for invalid in (True, 1, None, "false"):
                self.assertFalse(w.approved_native_receipt({**NATIVE,key:invalid}))

    def test_exact_node_durable_stop_requires_exit_zero(self):
        self.assertTrue(w.approved_node_stop(NODE,0))
        self.assertFalse(w.approved_node_stop(NODE,1))
        self.assertFalse(w.approved_node_stop(None,0))

    def test_forged_disk_readback_and_batch_count_refused(self):
        for invalid in (False, None, 1, "true"):
            self.assertFalse(w.approved_node_stop({
                **NODE, "durable_three_reopened":invalid,
            },0))
        for invalid in (0,2,True,1.0,"1",None):
            self.assertFalse(w.approved_node_stop({
                **NODE, "accepted_batches":invalid,
            },0))
        self.assertFalse(w.approved_node_stop({
            **NODE,"phase":"wave190_listening",
        },0))

    def test_existing_scratch_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave190-guard-") as temp:
            root=Path(temp)
            (root/"KEEP").write_text("not ours")
            with patch.object(w,"SCRATCH",root):
                with self.assertRaisesRegex(ValueError,"already_exists"):
                    w.scratch_prepare()
            self.assertEqual((root/"KEEP").read_text(),"not ours")

    def test_changed_original_rust_proto_file_refused(self):
        with patch.object(w.node_attest,"admitted"), patch.object(
            w.node_attest,"checked_dependencies"
        ), patch.object(w.node_attest,"original_blob",return_value=("a"*40,b"fake source bytes")):
            with self.assertRaisesRegex(ValueError,"original_rust_proto_source_changed"):
                w.verify_first_party_fixture()

    def test_no_production_qualification_even_with_valid_synthetic_receipt(self):
        self.assertFalse(w.REPORT["production_rust_consumer_qualified"])
        self.assertFalse(w.REPORT["production_node_pipeline_qualified"])
        self.assertFalse(w.REPORT["authenticated_tenant_isolation_qualified"])
        self.assertFalse(w.REPORT["release_qualified"])

    def test_actual_pinned_first_party_source_and_lock_on_connected_mac(self):
        if not Path("/private/tmp/flind-wave190-rust-kafka-node/Cargo.lock").is_file():
            self.skipTest("No connected, pinned Mac fixture available")
        w.verify_first_party_fixture()

if __name__=="__main__":
    unittest.main()
