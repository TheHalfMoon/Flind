"""Wave190 fail-closed native Kafka/Rust/Node/durable ClickHouse qualification guards."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.flind import qualify_native_rust_node_durable_chain_wave190 as w
from tools.flind import qualify_actual_node_grpc_http2_wire_wave186 as w186

GOOD={
    "native_kafka_three_events":True,
    "original_rust_proto_node_http2_ack_three":True,
    "native_rust_committed_offset":3,
    "production_rust_consumer_qualified":False,
    "production_node_pipeline_qualified":False,
    "release_qualified":False,
}
CHILD={
    "test_chain_pass":True,"native_committed_offset":3,
    "node_server_stopped":True,"release_qualified":False,
    "production_rust_ingester_qualified":False,
    "production_node_batch_driver_qualified":False,
}
PARENT={
    "kafka_431_broker_qualified":True,
    "real_kafka_producer_ack_qualified":True,
    "real_kafka_consumer_qualified":True,
    "local_clickhouse_relay_qualified":True,
    "owned_kafka_process_stopped":True,
    "owned_kafka_scratch_removed":True,
    "optional_private_kafka_probe":CHILD,
}

class CrossServiceAdmissionTests(unittest.TestCase):
    def test_only_exact_native_rust_offset_three_can_pass(self):
        self.assertTrue(w.native_ack_receipt_valid(GOOD))
        for value in (None,True,3.0,"3",0,2,4):
            self.assertFalse(w.native_ack_receipt_valid({**GOOD,"native_rust_committed_offset":value}))
    def test_reject_false_or_forged_native_grpc_success(self):
        for name in ("native_kafka_three_events","original_rust_proto_node_http2_ack_three"):
            self.assertFalse(w.native_ack_receipt_valid({**GOOD,name:False}))
        self.assertFalse(w.native_ack_receipt_valid(None))
    def test_no_product_release_or_native_production_promotions(self):
        for name in ("production_rust_consumer_qualified","production_node_pipeline_qualified","release_qualified"):
            self.assertFalse(w.native_ack_receipt_valid({**GOOD,name:True}))
    def test_unowned_scratch_refused_before_any_service(self):
        with TemporaryDirectory(prefix="flind-wave190-unit-",dir="/private/tmp") as name:
            with patch.object(w,"run_kafka") as kafka:
                result=w.qualify(Path("/fake"),Path("/fake"),Path("/fake"),Path("/fake"),Path(name),Path("/fake"))
            kafka.assert_not_called()
            self.assertEqual(result["blocker"],"unowned_wave190_scratch")
            self.assertFalse(result["release_qualified"])
    def mocked(self,child=None, parent=None):
        with TemporaryDirectory(prefix="flind-wave190-unit-",dir="/private/tmp") as name:
            root=Path(name)
            (root/".flind-wave190-owner").write_text("FLIND_WAVE190_TEST_CHAIN_V1\n")
            old=Path("/private/tmp/flind-wave76-frontend")
            if not old.is_dir():
                self.skipTest("Mac source fixture unavailable")
            with patch.object(w,"admitted"), patch.object(w,"checked_dependencies"), patch.object(
                w,"original_sources",return_value={"test":"sha"}
            ), patch.object(w,"attested_supported_runtime",return_value=(Path("/fake"),{})),patch.object(
                w186,"original_blob",side_effect=lambda repo,p:("a"*40,(old/p).read_bytes())
            ), patch.object(w,"run_kafka",return_value=parent or {
                **PARENT,"optional_private_kafka_probe":CHILD if child is None else child
            }):
                return w.qualify(old,old,old,old,root,Path("/fake"))
    def test_matching_synthetic_mock_does_not_promote_release(self):
        result=self.mocked()
        self.assertTrue(result["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"])
        self.assertFalse(result["production_rust_ingester_qualified"])
        self.assertFalse(result["production_node_batch_driver_qualified"])
        self.assertFalse(result["release_qualified"])
    def test_missing_or_wrong_offset_fails_combined_gate(self):
        for offset in (None,2,4,True,3.0):
            result=self.mocked(child={**CHILD,"native_committed_offset":offset})
            self.assertFalse(result["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"])
            self.assertFalse(result["release_qualified"])
    def test_missing_clean_shutdown_fails_combined_gate(self):
        result=self.mocked(child={**CHILD,"node_server_stopped":False})
        self.assertFalse(result["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"])
    def test_forged_prod_driver_release_flags_fail_combined_gate(self):
        for field in ("production_node_batch_driver_qualified","production_rust_ingester_qualified","release_qualified"):
            result=self.mocked(child={**CHILD,field:True})
            self.assertFalse(result["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"])
            self.assertFalse(result["release_qualified"])
    def test_missing_real_kafka_or_cleanup_fails_combined_gate(self):
        for field in ("kafka_431_broker_qualified","real_kafka_consumer_qualified",
                      "owned_kafka_process_stopped","owned_kafka_scratch_removed"):
            result=self.mocked(parent={**PARENT,field:False})
            self.assertFalse(result["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"])
if __name__=="__main__":
    unittest.main()
