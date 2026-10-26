"""Wave122 fail-safe Rust Kafka/gRPC E2E receipt guards."""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from tools.flind import qualify_rust_ingestion_failures_wave122 as q
from tools.flind.qualify_original_rust_grpc_kafka_wave121 import APPROVED_CASES, FAILURE_CASES


class RustFailureModesWave122(TestCase):
    def test_three_original_failure_cases_are_approved(self):
        self.assertEqual(len(FAILURE_CASES), 3)
        self.assertEqual(len(set(FAILURE_CASES)), 3)
        self.assertTrue(set(FAILURE_CASES).issubset(APPROVED_CASES))
        self.assertIn("lost_ack_after_processing_replays_without_loss", FAILURE_CASES)
        self.assertIn("poison_batch_fails_safely_without_committing", FAILURE_CASES)
        self.assertIn("partial_acceptance_fails_the_batch_without_commit", FAILURE_CASES)

    def test_all_three_original_results_are_required(self):
        receipt = {
            "native_rust_kafka_grpc_offset_frontier_qualified": True,
            "isolated_real_kafka_431": True,
            "native_test_receipt": {
                "full_checkout_original_source_restored": True,
                "actual_first_party_test_results": {case: True for case in FAILURE_CASES},
            },
        }
        with patch.object(q, "native_qualify", return_value=receipt) as qualifier:
            result = q.qualify()
        qualifier.assert_called_once_with(tests=FAILURE_CASES)
        self.assertTrue(result["native_rust_kafka_grpc_failure_replay_qualified"])
        self.assertTrue(result["lost_ack_replayed_without_loss"])
        self.assertTrue(result["poison_4xx_did_not_count_as_success"])
        self.assertTrue(result["partial_acceptance_no_commit"])
        self.assertTrue(result["test_checkout_original_sources_restored"])
        self.assertFalse(result["release_qualified"])

    def test_missing_one_case_refuses_integrated_pass(self):
        for absent in FAILURE_CASES:
            receipt = {
                "native_rust_kafka_grpc_offset_frontier_qualified": True,
                "isolated_real_kafka_431": True,
                "native_test_receipt": {
                    "actual_first_party_test_results": {
                        case: True for case in FAILURE_CASES if case != absent
                    }
                },
            }
            with self.subTest(absent=absent), patch.object(q, "native_qualify", return_value=receipt):
                self.assertFalse(q.qualify()["native_rust_kafka_grpc_failure_replay_qualified"])

    def test_failed_one_case_refuses_integrated_pass(self):
        for failed in FAILURE_CASES:
            receipt = {
                "native_rust_kafka_grpc_offset_frontier_qualified": False,
                "isolated_real_kafka_431": True,
                "blocker": "Synthetic failure fixture did not qualify",
                "native_test_receipt": {
                    "actual_first_party_test_results": {
                        case: case != failed for case in FAILURE_CASES
                    }
                },
            }
            with self.subTest(failed=failed), patch.object(q, "native_qualify", return_value=receipt):
                actual = q.qualify()
                self.assertFalse(actual["native_rust_kafka_grpc_failure_replay_qualified"])
                self.assertFalse(actual["release_qualified"])

    def test_product_delivery_gates_never_promoted(self):
        receipt = {
            "native_rust_kafka_grpc_offset_frontier_qualified": True,
            "isolated_real_kafka_431": True,
            "native_test_receipt": {
                "actual_first_party_test_results": {case: True for case in FAILURE_CASES}
            },
        }
        with patch.object(q, "native_qualify", return_value=receipt):
            actual = q.qualify()
        for name in (
            "production_node_worker_qualified",
            "production_clickhouse_ingestion_qualified",
            "authenticated_tenant_query_qualified",
            "browser_dashboard_qualified",
            "release_qualified",
        ):
            self.assertFalse(actual[name], name)


if __name__ == "__main__":
    import unittest
    unittest.main()
