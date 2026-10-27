"""Wave188 source-supported official ClickHouse MergeTree persistence admission."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind import qualify_supported_mergetree_durable_wave188 as w


class DurableSupportedClickHouseGuards(unittest.TestCase):
    def test_pinned_official_version_and_sha256(self):
        self.assertEqual(w.EXPECTED_VERSION, "25.12.7.21")
        self.assertEqual(len(w.OFFICIAL_MAC_ARM64_SHA256), 64)
        self.assertEqual(w.FREE_DISK_FLOOR, 5 * 1024 ** 3)

    def test_unmarked_scratch_refused_before_binary_execution(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            bin = root / "clickhouse-original-compressed-aarch64"
            bin.write_bytes(b"untrusted")
            with patch.object(w, "checked_scratch"), patch.object(w.subprocess, "run") as process:
                with self.assertRaisesRegex(w.Refused, "not_owned_wave188_scratch"):
                    w.checked_runtime(Path("/fake"), root, bin)
                process.assert_not_called()

    def test_wrong_binary_scope_refused(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            (root / w.OWNER_FILE).write_text(w.OWNER_TEXT)
            with patch.object(w, "checked_scratch"):
                with self.assertRaisesRegex(w.Refused, "unsupported_clickhouse_binary_scope"):
                    w.checked_runtime(Path("/fake"), root, Path("/bin/echo"))

    def test_modified_or_short_clickhouse_asset_refused(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            (root / w.OWNER_FILE).write_text(w.OWNER_TEXT)
            bin = root / "fake-official"
            bin.write_bytes(b"not a signed official ClickHouse binary")
            with patch.object(w, "checked_scratch"), patch.object(w.subprocess, "run") as command:
                with self.assertRaisesRegex(w.Refused, "clickhouse_official_asset_size_mismatch"):
                    w.checked_runtime(Path("/fake"), root, bin)
                command.assert_not_called()

    def test_process_count_restricted_to_four(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            for index in (0, 5, -1):
                with self.assertRaisesRegex(w.Refused, "session_count_budget"):
                    w.process_query(Path("/bin/echo"), root, root / "state", "SELECT 1", index)

    def test_existing_process_output_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            out = root / "wave188-process-1.jsonl"
            out.write_text("MUST STAY")
            with patch.object(w.subprocess, "run") as command:
                with self.assertRaisesRegex(w.Refused, "unowned_clickhouse_process_output"):
                    w.process_query(Path("/bin/echo"), root, root / "state", "SELECT 1", 1)
                command.assert_not_called()
            self.assertEqual(out.read_text(), "MUST STAY")

    def test_existing_disk_session_refused_without_writes(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            (root / "wave188-durable-session").mkdir()
            with patch.object(w, "checked_runtime", return_value=("a" * 40, w.EXPECTED_COLUMNS, Path("/fake"))), patch.object(w, "process_query") as process:
                result = w.qualify(Path("/fake"), root, Path("/fake"))
                process.assert_not_called()
            self.assertEqual(result["blocker"], "persisted_session_already_exists")
            self.assertFalse(result["release_qualified"])

    def make_fake_steps(self, scratch: Path, corrupt: bool = False):
        rows = w.fixture()
        fifth = {
            "uuid": "00000000-0000-4000-8000-000000000005",
            "team_id": 101, "event": "flind_team_a_return",
        }
        def projected(row):
            return {k: row[k] for k in ("uuid", "team_id", "event")}
        def fake_process(binary, scratch_arg, session, sql, index):
            self.assertEqual(scratch_arg, scratch)
            if index == 1:
                checksum = session / "store" / "test" / "checksums.txt"
                checksum.parent.mkdir(parents=True, exist_ok=True)
                checksum.write_text("synthetic part fixture")
                return [{"team_id": 101, "event_count": 2}, {"team_id": 202, "event_count": 2}]
            if index == 2:
                return sorted([projected(row) for row in rows], key=lambda row: row["uuid"])
            if index == 3:
                return [{"team_id": 101, "event_count": 3}]
            if index == 4:
                result = [
                    {"team_id": 101, "event_count": 3},
                    {"team_id": 202, "event_count": 2},
                ] + sorted([projected(row) for row in [*rows, fifth]], key=lambda row: row["uuid"])
                if corrupt:
                    result[3]["team_id"] = 202 if result[3]["team_id"] == 101 else 101
                return result
            raise AssertionError(f"unexpected stage {index}")
        return fake_process

    def test_four_successful_fake_receipts_never_promote_release(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            with patch.object(w, "checked_runtime", return_value=("a"*40, w.EXPECTED_COLUMNS, Path("/fake"))), patch.object(
                w, "process_query", side_effect=self.make_fake_steps(root)
            ) as process:
                result = w.qualify(Path("/fake"), root, Path("/fake"))
            self.assertEqual(process.call_count, 4)
            self.assertTrue(result["mergetree_persisted_across_four_processes"])
            self.assertEqual(result["synthetic_events_persisted"], 5)
            for key in ("native_kafka_to_clickhouse_qualified", "authenticated_tenant_isolation_qualified",
                        "sdk_api_dashboard_qualified", "release_qualified"):
                self.assertFalse(result[key])

    def test_cross_team_data_corruption_cannot_be_qualified(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="flind-wave188-unit-") as td:
            root = Path(td)
            with patch.object(w, "checked_runtime", return_value=("a"*40, w.EXPECTED_COLUMNS, Path("/fake"))), patch.object(
                w, "process_query", side_effect=self.make_fake_steps(root, corrupt=True)
            ):
                result = w.qualify(Path("/fake"), root, Path("/fake"))
            self.assertFalse(result["mergetree_persisted_across_four_processes"])
            self.assertEqual(result["blocker"], "durable_mergetree_event_content_mismatch")
            self.assertFalse(result["release_qualified"])


if __name__ == "__main__":
    unittest.main()
