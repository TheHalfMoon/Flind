"""Wave226: no database access if first-party destructive reset *bodies* drift."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.e2e import schema_preflight_wave216 as gate


class Wave226ResetSourceDigests(unittest.TestCase):
    def test_original_source_matches_all_three_reviewed_digests(self):
        self.assertTrue(gate.validate_original_reset_contract())
        common = gate._source_segment(
            gate.SQL_HELPER, "export const POSTGRES_DELETE_COMMON_TABLES_QUERY = " + chr(96), chr(96)
        )
        persons = gate._source_segment(
            gate.SQL_HELPER, "export const POSTGRES_DELETE_PERSONS_TABLES_QUERY = " + chr(96), chr(96)
        )
        clickhouse = gate._source_segment(
            gate.CH_HELPER, "    async resetTestDatabase(): Promise<void> {",
            "    // Topics that this database",
        )
        self.assertEqual(
            tuple(hashlib.sha256(section.encode("utf-8")).hexdigest()
                  for section in (common, persons, clickhouse)),
            gate.RESET_SEGMENT_SHA256,
        )

    def test_extra_non_posthog_delete_refused_before_any_service_probe(self):
        original = gate.SQL_HELPER.read_text()
        query = "DELETE FROM posthog_team CASCADE;"
        self.assertEqual(original.count(query), 1)
        altered = original.replace(query, query + " DELETE FROM customer_data CASCADE;", 1)
        self._reject_drift("SQL_HELPER", altered)

    def test_changed_dynamic_delete_expression_refused(self):
        original = gate.SQL_HELPER.read_text()
        expression = "quote_ident(r.tablename) || ' CASCADE'"
        self.assertEqual(original.count(expression), 2)
        altered = original.replace(expression, "r.tablename || ' CASCADE'", 1)
        self._reject_drift("SQL_HELPER", altered)

    def test_persons_reset_body_change_refused(self):
        original = gate.SQL_HELPER.read_text()
        query = "DELETE FROM posthog_person CASCADE;"
        self.assertEqual(original.count(query), 1)
        altered = original.replace(query, query + " DELETE FROM customer_data CASCADE;", 1)
        self._reject_drift("SQL_HELPER", altered)

    def test_clickhouse_reset_guard_removal_refused(self):
        original = gate.CH_HELPER.read_text()
        guard = "assertIsolatedClickhouseReset(phase1, 1, isolatedE2E)"
        self.assertEqual(original.count(guard), 1)
        altered = original.replace(guard, "void phase1", 1)
        self._reject_drift("CH_HELPER", altered)

    def test_unrelated_source_comment_outside_reset_is_not_blocked(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave226-") as folder:
            replacement = Path(folder) / "sql.ts"
            replacement.write_text(gate.SQL_HELPER.read_text() + "\n// unrelated comment\n")
            with patch.object(gate, "SQL_HELPER", replacement):
                self.assertTrue(gate.validate_original_reset_contract())

    def test_hashes_do_not_claim_schema_or_release_qualification(self):
        # This contract approves only the destructive reset *source* itself.
        self.assertEqual(len(gate.RESET_SEGMENT_SHA256), 3)
        self.assertTrue(all(len(h) == 64 for h in gate.RESET_SEGMENT_SHA256))

    def _reject_drift(self, field: str, content: str) -> None:
        with tempfile.TemporaryDirectory(prefix="flind-wave226-") as folder:
            replacement = Path(folder) / "altered.ts"
            replacement.write_text(content)
            with patch.object(gate, field, replacement):
                with patch.object(gate, "inspect", side_effect=AssertionError("service touched")):
                    with self.assertRaisesRegex(ValueError, "reset source digest changed"):
                        gate.preflight()


if __name__ == "__main__":
    unittest.main()
