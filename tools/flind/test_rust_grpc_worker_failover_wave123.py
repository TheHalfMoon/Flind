"""Wave123 native Rust worker failover: allowlist and scope tests."""
from unittest import TestCase
from unittest.mock import patch

from tools.flind import qualify_rust_grpc_worker_failover_wave123 as q
from tools.flind.qualify_original_rust_grpc_kafka_wave121 import (
    APPROVED_CASES, RECOVERY_CASES,
)


class NativeWorkerFailoverWave123(TestCase):
    def test_exact_original_recovery_cases_approved(self):
        self.assertEqual(len(RECOVERY_CASES), 3)
        self.assertTrue(set(RECOVERY_CASES).issubset(set(APPROVED_CASES)))
        self.assertEqual(len(RECOVERY_CASES), len(set(RECOVERY_CASES)))
        for name in RECOVERY_CASES:
            self.assertRegex(name, r"^[a-z0-9_]+$")

    def test_all_original_test_cases_have_to_pass(self):
        fixture = {
            "native_rust_kafka_grpc_offset_frontier_qualified": True,
            "isolated_real_kafka_431": True,
            "native_test_receipt": {
                "full_checkout_original_source_restored": True,
                "actual_first_party_test_results": {name: True for name in RECOVERY_CASES},
            },
        }
        with patch.object(q, "actual_native", return_value=fixture) as call:
            result = q.qualify()
        call.assert_called_once_with(tests=RECOVERY_CASES)
        self.assertTrue(result["real_rust_kafka_grpc_worker_failover_qualified"])
        self.assertTrue(result["worker_health_failover_preserved_sequence"])
        self.assertTrue(result["draining_worker_crash_replayed_to_survivor"])
        self.assertTrue(result["nacked_worker_fenced_and_rerouted"])

    def test_missing_case_or_unrestored_checkout_blocks_qualification(self):
        for absent in RECOVERY_CASES:
            fixture = {
                "native_rust_kafka_grpc_offset_frontier_qualified": True,
                "isolated_real_kafka_431": True,
                "native_test_receipt": {
                    "full_checkout_original_source_restored": True,
                    "actual_first_party_test_results": {
                        name: True for name in RECOVERY_CASES if name != absent
                    },
                },
            }
            with self.subTest(absent=absent), patch.object(q, "actual_native", return_value=fixture):
                self.assertFalse(q.qualify()["real_rust_kafka_grpc_worker_failover_qualified"])

        fixture = {
            "native_rust_kafka_grpc_offset_frontier_qualified": True,
            "isolated_real_kafka_431": True,
            "native_test_receipt": {
                "full_checkout_original_source_restored": False,
                "actual_first_party_test_results": {name: True for name in RECOVERY_CASES},
            },
        }
        with patch.object(q, "actual_native", return_value=fixture):
            self.assertFalse(q.qualify()["real_rust_kafka_grpc_worker_failover_qualified"])

    def test_production_node_and_release_flags_always_false(self):
        fixture = {
            "native_rust_kafka_grpc_offset_frontier_qualified": True,
            "isolated_real_kafka_431": True,
            "native_test_receipt": {
                "full_checkout_original_source_restored": True,
                "actual_first_party_test_results": {name: True for name in RECOVERY_CASES},
            },
        }
        with patch.object(q, "actual_native", return_value=fixture):
            result = q.qualify()
        for field in (
            "actual_nodejs_worker_qualified",
            "durable_production_events_schema_qualified",
            "tenant_authenticated_dashboard_qualified",
            "release_qualified",
        ):
            self.assertFalse(result[field], field)


if __name__ == "__main__":
    import unittest
    unittest.main()
