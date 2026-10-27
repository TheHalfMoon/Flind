"""Wave178 source-backed ClickHouse local Memory INSERT regression guards."""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import (
    EXPECTED_COLUMNS, SCHEMA_PATH, SCRATCH_MARKER, SCRATCH_MARKER_TEXT,
    ProbeBlocked, fixture,
)
from tools.flind.qualify_local_clickhouse_insert_wave178 import (
    MAX_STATEMENTS, insert_sql, query_plan, run_insert,
)


class ClickHouseInsertTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="flind-ch178-unit-", dir="/private/tmp")
        self.base = Path(self.temp.name)
        self.repo = self.base / "source"
        self.scratch = self.base / "scratch"
        self.repo.mkdir()
        self.scratch.mkdir()
        (self.scratch / SCRATCH_MARKER).write_text(SCRATCH_MARKER_TEXT)
        (self.repo / "pyproject.toml").write_text("[project]\nname='flind'\nversion='0.1.0'\n")
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        source = self.repo / SCHEMA_PATH
        source.parent.mkdir(parents=True)
        source.write_text('database "posthog" {\n table "events_recent" {\n' + "".join(
            f' column "{field}" {{\n type = "{kind}"\n }}\n'
            for field, kind in EXPECTED_COLUMNS.items()
        ) + " }\n}\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.repo), "-c", "user.name=Flind Tests",
            "-c", "user.email=flind@invalid.example", "commit", "-qm", "test fixture",
        ], check=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_query_plan_actual_memory_ddl_and_insert(self):
        statements = query_plan(fixture(), EXPECTED_COLUMNS)
        self.assertIn("CREATE TABLE events", statements)
        self.assertIn("ENGINE = Memory", statements)
        self.assertIn("INSERT INTO events", statements)
        self.assertIn("WHERE team_id = 101", statements)
        self.assertIn("WHERE team_id = 202", statements)
        self.assertIn("WHERE team_id = 303", statements)
        self.assertIn("FORMAT JSONEachRow", statements)
        self.assertEqual(statements.count(";\n"), 7)
        self.assertGreaterEqual(MAX_STATEMENTS, 7)

    def test_schema_change_is_not_accepted(self):
        mismatch = {**EXPECTED_COLUMNS, "team_id": "String"}
        with self.assertRaisesRegex(ProbeBlocked, "first_party_schema_not_verified"):
            query_plan(fixture(), mismatch)
        with self.assertRaisesRegex(ProbeBlocked, "first_party_schema_not_verified"):
            insert_sql(fixture(), mismatch)

    def test_unapproved_row_shape_refused(self):
        bad = [{**fixture()[0], "extra": "injected"}]
        with self.assertRaises(ProbeBlocked):
            insert_sql(bad, EXPECTED_COLUMNS)
        bad = [{**fixture()[0], "team_id": 303}]
        with self.assertRaises(ProbeBlocked):
            insert_sql(bad, EXPECTED_COLUMNS)

    def test_noninteger_team_id_refused(self):
        for value in (101.0, True, "101", None):
            with self.assertRaises(ProbeBlocked):
                insert_sql([{**fixture()[0], "team_id": value}], EXPECTED_COLUMNS)

    def test_unbounded_row_count_fails_closed(self):
        for rows in ([], fixture() * 6):
            with self.assertRaises(ProbeBlocked):
                insert_sql(rows, EXPECTED_COLUMNS)

    def test_single_quote_escaped_in_synthetic_value(self):
        rows = [{**fixture()[0], "event": "flind_test's_signup"}]
        sql = insert_sql(rows, EXPECTED_COLUMNS)
        self.assertIn("flind_test''s_signup", sql)

    def test_zero_bytes_and_invalid_type_rejected(self):
        rows = [{**fixture()[0], "event": "flind_bad\x00event"}]
        with self.assertRaises(ProbeBlocked):
            insert_sql(rows, EXPECTED_COLUMNS)
        rows = [{**fixture()[0], "event": {"not": "string"}}]
        with self.assertRaises(ProbeBlocked):
            insert_sql(rows, EXPECTED_COLUMNS)

    def test_missing_scratch_marker_fails_before_engine(self):
        (self.scratch / SCRATCH_MARKER).unlink()
        result = run_insert(self.repo, self.scratch)
        self.assertFalse(result["real_clickhouse_insert_qualified"])
        self.assertFalse(result["release_qualified"])
        self.assertIn("blocker", result)

    def test_missing_clickhouse_binary_fails_closed(self):
        report = run_insert(
            self.repo, self.scratch, clickhouse="/private/tmp/flind-does-not-exist",
        )
        self.assertTrue(report["first_party_schema_verified"])
        self.assertEqual(report["blocker"], "clickhouse_not_found")
        self.assertFalse(report["release_qualified"])

    def test_preexisting_engine_session_refused(self):
        (self.scratch / "wave178-memory-session").mkdir()
        report = run_insert(self.repo, self.scratch, clickhouse="/opt/homebrew/bin/clickhouse")
        self.assertEqual(report["blocker"], "memory_session_exists")
        self.assertFalse(report["real_clickhouse_insert_qualified"])

    def test_source_code_explicitly_detaches_clickhouse_stdin(self):
        source = Path(__file__).with_name(
            "qualify_local_clickhouse_insert_wave178.py"
        )
        parsed = ast.parse(source.read_text())
        self.assertTrue(any(
            isinstance(k, ast.keyword)
            and k.arg == "stdin"
            and isinstance(k.value, ast.Attribute)
            and k.value.attr == "DEVNULL"
            for node in ast.walk(parsed) if isinstance(node, ast.Call)
            for k in node.keywords
        ))

    def test_tenant_and_release_never_promoted_by_missing_binary(self):
        receipt = run_insert(self.repo, self.scratch, clickhouse="/private/tmp/flind-missing")
        for name in (
            "authenticated_tenant_isolation_qualified",
            "first_party_sdk_ingestion_qualified",
            "kafka_ingestion_qualified",
            "api_dashboard_qualified",
            "mergetree_persistence_qualified",
            "release_qualified",
        ):
            self.assertFalse(receipt[name])


if __name__ == "__main__":
    unittest.main()
