#!/usr/bin/env python3
"""Wave123: real first-party Rust/Kafka/gRPC worker failover and drain E2E.

The actual production Rust consumer and actual private Kafka 4.3.1 broker
are exercised with the original in-crate test WorkerIngest gRPC workers.
Not a real Node worker or product ClickHouse flow.
"""
from __future__ import annotations

import json

from tools.flind.qualify_original_rust_grpc_kafka_wave121 import RECOVERY_CASES, qualify as actual_native


def qualify() -> dict:
    native = actual_native(tests=RECOVERY_CASES)
    child = native.get("native_test_receipt") or {}
    tests = child.get("actual_first_party_test_results") or {}
    passed = (
        native.get("native_rust_kafka_grpc_offset_frontier_qualified") is True
        and len(tests) == len(RECOVERY_CASES)
        and all(tests.get(case) is True for case in RECOVERY_CASES)
        and child.get("full_checkout_original_source_restored") is True
    )
    return {
        "real_rust_kafka_grpc_worker_failover_qualified": passed,
        "original_in_tree_rust_e2e_tests": tests,
        "actual_kafka_431_broker": native.get("isolated_real_kafka_431") is True,
        "worker_health_failover_preserved_sequence": tests.get(RECOVERY_CASES[0]) is True,
        "draining_worker_crash_replayed_to_survivor": tests.get(RECOVERY_CASES[1]) is True,
        "nacked_worker_fenced_and_rerouted": tests.get(RECOVERY_CASES[2]) is True,
        "source_test_checkout_restored": child.get("full_checkout_original_source_restored") is True,
        "actual_nodejs_worker_qualified": False,
        "durable_production_events_schema_qualified": False,
        "tenant_authenticated_dashboard_qualified": False,
        "release_qualified": False,
        **({"blocker": native.get("blocker") or "Original worker failover E2E not qualified"}
           if not passed else {}),
    }


if __name__ == "__main__":
    result = qualify()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["real_rust_kafka_grpc_worker_failover_qualified"] else 2)
