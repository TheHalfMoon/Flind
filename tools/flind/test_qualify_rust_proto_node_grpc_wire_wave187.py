"""Wave187: source, scratch, forged ack and release-promotion guard tests."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.flind import qualify_rust_proto_node_grpc_wire_wave187 as w

NATIVE = {
 "original_rust_proto_client_wire_pass":True,
 "real_node_http2_ack_verified":True,
 "bad_rust_seq_refused":True,
 "production_rust_ingestion_consumer_qualified":False,
 "production_node_driver_qualified":False,
 "durable_clickhouse_qualified":False,
 "release_qualified":False,
}
STOP = {"flind_wave187":"server_stopped","accepted_synthetic_batches":1}


class OriginalRustToNodeWireGuards(unittest.TestCase):
    def test_expected_original_proto_file_inventory(self):
        self.assertEqual(len(w.RUST_PROTO_SOURCE),3)
        self.assertEqual(len(w.SUCCESS),3)
        self.assertEqual(len(w.FALSE),4)

    def test_exact_well_formed_native_wire_ack(self):
        self.assertTrue(w.receipt_ok(NATIVE,STOP))
        self.assertFalse(w.receipt_ok(None,STOP))
        self.assertFalse(w.receipt_ok(NATIVE,None))

    def test_fake_native_ack_and_missing_ready_refused(self):
        for key in w.SUCCESS:
            self.assertFalse(w.receipt_ok({**NATIVE,key:False},STOP),key)
        self.assertFalse(w.receipt_ok({**NATIVE,"real_node_http2_ack_verified":None},STOP))

    def test_fake_prod_rust_consumer_and_release_claims_refused(self):
        for key in w.FALSE:
            self.assertFalse(w.receipt_ok({**NATIVE,key:True},STOP),key)

    def test_extra_acks_and_missing_shutdown_rejected(self):
        for value in (0,2,-1,True,"1",1.0):
            self.assertFalse(w.receipt_ok(NATIVE,{**STOP,"accepted_synthetic_batches":value}))
        self.assertFalse(w.receipt_ok(NATIVE,{**STOP,"flind_wave187":"listening"}))

    def test_unmarked_temp_rust_scratch_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave187-",dir="/private/tmp") as temp:
            with self.assertRaises(w.Rejected):
                w.original_rust_sources(Path("/tmp/repo"),Path("/tmp/repo"),Path("/tmp/repo"),Path(temp))

    def test_wrong_rust_source_cannot_pass_source_gate(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave187-",dir="/private/tmp") as temp:
            root=Path(temp)
            (root/w.RUST_MARKER).write_text(w.RUST_MARKER_VALUE)
            with patch.object(w.w186,"original_blob",return_value=("a"*40,b"original")):
                with self.assertRaises(w.Rejected):
                    w.original_rust_sources(root,root,root,root)

    def test_qualified_fixture_stays_not_product_qualified(self):
        ref=Path("/private/tmp/flind-wave171-current-boot")
        old=Path("/private/tmp/flind-wave76-frontend")
        runner=Path("/private/tmp/flind-wave164-runner")
        node=Path("/private/tmp/flind-wave186-grpc-core")
        rust=Path("/private/tmp/flind-wave187-rust-node-client")
        if not all(p.is_dir() for p in (ref,old,runner,node,rust)):
            self.skipTest("Mac source-attested scratch fixtures not connected")
        result=w.qualify(ref,old,runner,node,rust)
        self.assertTrue(result["original_rust_proto_to_real_node_grpc_qualified"],result)
        self.assertEqual(result["rust_node_ack_count"],1)
        self.assertTrue(result["node_server_stopped"])
        for key in ("production_rust_kafka_ingestion_consumer_qualified",
                    "production_node_ingestion_driver_qualified",
                    "durable_clickhouse_qualified","authenticated_tenant_isolation_qualified",
                    "release_qualified"):
            self.assertFalse(result[key],key)


if __name__=="__main__":
    unittest.main()
