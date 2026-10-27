"""Wave177: first-party schema attestation, bounded ClickHouse and team-scope guards."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import (
    EXPECTED_COLUMNS, SCHEMA_PATH, SCRATCH_MARKER, SCRATCH_MARKER_TEXT,
    ProbeBlocked, accept_team, checked_scratch, fixture, qualify,
    scoped_sql, verified_schema,
)


class ClickHouseTenantSQLTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="flind-ch177-", dir="/private/tmp")
        self.base = Path(self.temp.name)
        self.repo = self.base / "source"
        self.scratch = self.base / "scratch"
        self.repo.mkdir()
        self.scratch.mkdir()
        (self.scratch / SCRATCH_MARKER).write_text(SCRATCH_MARKER_TEXT)
        (self.repo / "pyproject.toml").write_text("[project]\nname='flind'\nversion='0.1.0'\n")
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        target = self.repo / SCHEMA_PATH
        target.parent.mkdir(parents=True)
        text = (
            'database "posthog" {\n  table "events_recent" {\n'
            + "".join(
                '    column "' + field + '" {\n      type = "' + kind + '"\n    }\n'
                for field, kind in EXPECTED_COLUMNS.items()
            )
            + "  }\n}\n"
        )
        target.write_text(text)
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.repo), "-c", "user.name=Flind Tests",
            "-c", "user.email=flind@invalid.example",
            "commit", "-qm", "synthetic first-party shape fixture",
        ], check=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_first_party_git_schema_integrity(self):
        sha, columns = verified_schema(self.repo, "HEAD")
        self.assertEqual(len(sha), 40)
        self.assertEqual(columns, EXPECTED_COLUMNS)

    def test_source_schema_type_change_fails_closed(self):
        schema = self.repo / SCHEMA_PATH
        schema.write_text(schema.read_text().replace('type = "Int64"', 'type = "String"'))
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(self.repo), "-c", "user.name=Flind Tests",
            "-c", "user.email=flind@invalid.example",
            "commit", "-qm", "unsafe tenant id type",
        ], check=True)
        with self.assertRaisesRegex(ProbeBlocked, "first_party_events_schema_mismatch"):
            verified_schema(self.repo, "HEAD")

    def test_all_queries_enforce_team_id_predicate(self):
        for team in (101, 202, 2**63 - 1):
            for kind in ("events", "counts"):
                sql = scoped_sql(team, kind=kind)
                self.assertIn(f"WHERE team_id = {team}", sql)
                self.assertIn("FROM events", sql)
                self.assertIn("FORMAT JSONEachRow", sql)

    def test_injection_and_invalid_identifiers_rejected(self):
        for value in (
            "101 OR 1=1", "101", "-1", 0, -1, True, False, None,
            1.0, {}, [], 2**63, 0.0001,
        ):
            with self.subTest(value=repr(value)), self.assertRaises(ProbeBlocked):
                accept_team(value)

    def test_unapproved_sql_query_kind_rejected(self):
        for kind in ("all", "unscoped", "", "UPDATE", "delete"):
            with self.assertRaises(ProbeBlocked):
                scoped_sql(101, kind=kind)

    def test_marked_isolated_scratch_admitted(self):
        checked_scratch(self.repo, self.scratch, "HEAD")

    def test_marker_missing_refuses_before_clickhouse(self):
        (self.scratch / SCRATCH_MARKER).unlink()
        with self.assertRaises(ProbeBlocked):
            checked_scratch(self.repo, self.scratch, "HEAD")
        result = qualify(self.repo, self.scratch)
        self.assertEqual(result["blocker"], "scratch_marker_missing")
        self.assertFalse(result["clickhouse_local_engine_qualified"])
        self.assertFalse(result["release_qualified"])

    def test_source_and_scratch_may_not_overlap(self):
        inside = self.repo / "scratch"
        inside.mkdir()
        (inside / SCRATCH_MARKER).write_text(SCRATCH_MARKER_TEXT)
        with self.assertRaisesRegex(ProbeBlocked, "source_scratch_overlap"):
            checked_scratch(self.repo, inside, "HEAD")

    def test_unsafe_git_ref_is_rejected_before_any_data_read(self):
        for ref in ("--upload-pack=bad", "../escape", "refs/../HEAD", ""):
            with self.assertRaises(ProbeBlocked):
                checked_scratch(self.repo, self.scratch, ref)

    def test_symlinked_scratch_and_marker_denied(self):
        link = self.base / "linked"
        link.symlink_to(self.scratch, target_is_directory=True)
        with self.assertRaises(ProbeBlocked):
            checked_scratch(self.repo, link, "HEAD")
        (self.scratch / SCRATCH_MARKER).unlink()
        marker = self.base / "marker"
        marker.write_text(SCRATCH_MARKER_TEXT)
        (self.scratch / SCRATCH_MARKER).symlink_to(marker)
        with self.assertRaises(ProbeBlocked):
            checked_scratch(self.repo, self.scratch, "HEAD")

    def test_fixture_contains_two_disjoint_synthetic_teams(self):
        rows = fixture()
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["team_id"] for row in rows}, {101, 202})
        self.assertEqual({row["team_id"] for row in rows if "team_a" in row["event"]}, {101})
        self.assertEqual({row["team_id"] for row in rows if "team_b" in row["event"]}, {202})

    def test_unavailable_clickhouse_fails_closed_without_release(self):
        result = qualify(self.repo, self.scratch, clickhouse="/private/tmp/flind-no-clickhouse")
        self.assertEqual(result["blocker"], "local_clickhouse_executable_missing")
        self.assertTrue(result["schema_from_tracked_flind"])
        for key in ("kafka_ingestion_qualified", "flind_sdk_ingestion_qualified",
                    "authenticated_tenant_isolation_qualified", "release_qualified"):
            self.assertFalse(result[key])


if __name__ == "__main__":
    unittest.main()
