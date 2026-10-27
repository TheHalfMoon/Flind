"""Wave191 fail-closed acknowledgment-loss and replay admission tests.

All tests in this file use entirely synthetic data; one validates the exact
Git-attested original Wave190 JavaScript fixture without invoking services.
"""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_native_kafka_ack_loss_replay_wave191 as w


class CrashBeforeAckAdmissionTests(unittest.TestCase):
    def test_original_node_fixture_crash_injected_only_after_disk_verification(self):
        original = (w.base.ROOT / "tools/flind/verify_native_kafka_node_durable_wave190.mjs").read_bytes()
        derived = w.derived_fixture(original, crash=True).decode()
        self.assertEqual(derived.count("process.exit(73)"), 1)
        self.assertLess(derived.index("    verified=true"), derived.index("process.exit(73)"))
        self.assertLess(derived.index("process.exit(73)"), derived.index("    const ack="))
        self.assertIn("row.uuid!==uuid(i)", derived)

    def test_original_node_fixture_recovery_skips_only_test_insert(self):
        original = (w.base.ROOT / "tools/flind/verify_native_kafka_node_durable_wave190.mjs").read_bytes()
        recovery = w.derived_fixture(original, crash=False).decode()
        self.assertIn("    const start=[]", recovery)
        self.assertNotIn("INSERT INTO events VALUES", recovery)
        self.assertIn("SELECT uuid,team_id,event,properties,distinct_id", recovery)
        self.assertIn("if (rows.length!==3", recovery)
        self.assertIn("    const ack=", recovery)

    def test_modified_or_unverified_upstream_fixture_denied(self):
        original = (w.base.ROOT / "tools/flind/verify_native_kafka_node_durable_wave190.mjs").read_bytes()
        with self.assertRaisesRegex(w.Rejected, "source_changed"):
            w.derived_fixture(original+b" ", crash=True)
        with self.assertRaisesRegex(w.Rejected, "source_changed"):
            w.derived_fixture(b"process.exit(73)", crash=False)

    def test_original_uuid_team_event_invariants(self):
        self.assertEqual(len(w.EXPECTED_ROWS), 3)
        self.assertEqual(len({r["uuid"] for r in w.EXPECTED_ROWS}), 3)
        self.assertEqual([r["team_id"] for r in w.EXPECTED_ROWS], [101, 202, 101])

    @staticmethod
    def success():
        return {
            "node_exit_code": 0, "valid_original_rust_commit_receipt": True,
            "stop_receipt": {
                "phase": "wave190_stopped",
                "durable_three_reopened": True,
                "accepted_batches": 1,
            },
        }

    def test_mock_durable_replay_requires_exact_uncommitted_and_then_three(self):
        with patch.object(w, "kafka_committed", side_effect=[-1001,-1001,3]) as offset, patch.object(
            w, "node_fixture_install"
        ) as node, patch.object(
            w, "native_once", side_effect=[{"node_exit_code":73}, self.success()]
        ) as native, patch.object(
            w, "disk_rows", side_effect=[list(w.EXPECTED_ROWS),list(w.EXPECTED_ROWS)]
        ) as disk:
            result=w.test_broker("127.0.0.1:19092",Path("/fake"),Path("/fake"),b"placeholder")
        self.assertTrue(result["actual_ack_loss_replay_qualified"], result)
        self.assertEqual(result["original_rust_replayed_and_committed_offset"],3)
        self.assertEqual(offset.call_count,3)
        self.assertEqual(node.call_count,2)
        self.assertEqual(native.call_count,2)
        self.assertEqual(disk.call_count,2)
        self.assertFalse(result["release_qualified"])

    def test_commit_after_crash_fails_closed_without_recovery(self):
        with patch.object(w, "kafka_committed", side_effect=[-1001,3]), patch.object(
            w, "node_fixture_install"
        ), patch.object(w, "native_once", return_value={"node_exit_code":73}) as native, patch.object(
            w, "disk_rows", return_value=list(w.EXPECTED_ROWS)
        ):
            result=w.test_broker("127.0.0.1:19092",Path("/fake"),Path("/fake"),b"placeholder")
        self.assertFalse(result["actual_ack_loss_replay_qualified"])
        self.assertEqual(result["blocker"],"kafka_offset_committed_despite_missing_grpc_ack")
        self.assertEqual(native.call_count,1)

    def test_crash_without_actual_exit_73_denied(self):
        with patch.object(w, "kafka_committed",return_value=-1001),patch.object(
            w, "node_fixture_install"
        ),patch.object(w, "native_once",return_value={"node_exit_code":0}) as native:
            result=w.test_broker("127.0.0.1:19092",Path("/fake"),Path("/fake"),b"placeholder")
        self.assertFalse(result["actual_ack_loss_replay_qualified"])
        self.assertEqual(result["blocker"],"hard_crash_after_disk_not_observed")
        self.assertEqual(native.call_count,1)

    def test_durable_data_mismatch_never_recovered(self):
        with patch.object(w, "kafka_committed",return_value=-1001), patch.object(
            w, "node_fixture_install"
        ), patch.object(w, "native_once",return_value={"node_exit_code":73}), patch.object(
            w, "disk_rows",side_effect=w.Rejected("crash_replay_durable_uuid_team_event_mismatch")
        ):
            result=w.test_broker("127.0.0.1:19092",Path("/fake"),Path("/fake"),b"placeholder")
        self.assertFalse(result["actual_ack_loss_replay_qualified"])
        self.assertEqual(result["blocker"],"crash_replay_durable_uuid_team_event_mismatch")

    def test_missing_recovery_ack_must_not_qualify(self):
        with patch.object(w, "kafka_committed",side_effect=[-1001,-1001,3]), patch.object(
            w, "node_fixture_install"
        ), patch.object(w, "native_once",side_effect=[{"node_exit_code":73},{}]), patch.object(
            w, "disk_rows",return_value=list(w.EXPECTED_ROWS)
        ):
            result=w.test_broker("127.0.0.1:19092",Path("/fake"),Path("/fake"),b"placeholder")
        self.assertFalse(result["actual_ack_loss_replay_qualified"],result)

    def test_preexisting_scratch_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp",prefix="flind-wave191-unit-") as folder:
            root=Path(folder)
            sentinel=root/"KEEP_ORIGINAL_DATA"
            sentinel.write_text("unrelated")
            report=w.qualify(root)
            self.assertFalse(report["real_ack_lost_replay_integration_pass"])
            self.assertEqual(report["blocker"],"unsafe_or_preexisting_wave191_scratch")
            self.assertEqual(sentinel.read_text(),"unrelated")
            self.assertFalse(report["release_qualified"])

    def test_release_product_auth_flags_immutable_false(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp",prefix="flind-wave191-unit-") as folder:
            report=w.qualify(Path(folder))
            for flag in ("production_rust_ingestion_consumer_qualified",
                         "production_node_ingestion_driver_qualified",
                         "exactly_once_product_qualified",
                         "authenticated_tenant_isolation_qualified",
                         "release_qualified"):
                self.assertIs(report[flag], False)


if __name__ == "__main__":
    unittest.main()
