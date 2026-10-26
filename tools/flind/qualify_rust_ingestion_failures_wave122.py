#!/usr/bin/env python3
"""Wave122: original Rust Kafka/gRPC fail-safe E2E against a real Kafka broker.

Runs actual original crate tests: lost ACK replay, poison 4xx fail-closed,
and partial acceptance fail-closed. Worker is an in-crate protocol-compatible
test server, not production Node. Uses Wave121's bounded offline real harness.
"""
from __future__ import annotations

import json

from tools.flind.qualify_original_rust_grpc_kafka_wave121 import FAILURE_CASES, qualify as native_qualify


def qualify() -> dict:
    native = native_qualify(tests=FAILURE_CASES)
    evidence = (native.get("native_test_receipt") or {}).get("actual_first_party_test_results") or {}
    passed = bool(
        native.get("native_rust_kafka_grpc_offset_frontier_qualified") is True
        and len(evidence) == len(FAILURE_CASES)
        and all(evidence.get(name) is True for name in FAILURE_CASES)
    )
    return {
        "native_rust_kafka_grpc_failure_replay_qualified": passed,
        "original_first_party_rust_tests_passed": evidence,
        "actual_kafka_431_broker": native.get("isolated_real_kafka_431") is True,
        "test_checkout_original_sources_restored": (native.get("native_test_receipt") or {}).get(
            "full_checkout_original_source_restored"
        ) is True,
        "lost_ack_replayed_without_loss": evidence.get(FAILURE_CASES[0]) is True,
        "poison_4xx_did_not_count_as_success": evidence.get(FAILURE_CASES[1]) is True,
        "partial_acceptance_no_commit": evidence.get(FAILURE_CASES[2]) is True,
        "production_node_worker_qualified": False,
        "production_clickhouse_ingestion_qualified": False,
        "authenticated_tenant_query_qualified": False,
        "browser_dashboard_qualified": False,
        "release_qualified": False,
        **({"blocker": native.get("blocker") or "Three in-tree failure-mode cases not qualified"}
           if not passed else {}),
    }


if __name__ == "__main__":
    receipt = qualify()
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["native_rust_kafka_grpc_failure_replay_qualified"] else 2)
