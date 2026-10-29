"""Source-pinned local ClickHouse schema slice; never full migration qualification.

Only execute an adapted, unreplicated MergeTree table in an owner-disposable
/private/tmp location. Original cluster/replication, migration runner, Kafka,
materialized views, external services, and release remain NOT qualified.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = "posthog/clickhouse/migrations/0294_logs_volume_buckets.py"
PINNED_GIT_BLOB = "e726579705c5760b0814ab9a6d2bfe61dd096160"
DATABASE = "flind_wave248_synthetic"
TABLE = "logs_volume_buckets"
MARKER = "FLIND_WAVE248_LOCAL_CH_ONLY_V1\n"
CH_BINARY = Path("/opt/homebrew/bin/clickhouse")
MIN_DISK_FREE = 17 * 1024**3
MAX_MEMORY_BYTES = 512 * 1024**2


def original_source() -> str:
    """Require the exact Git-committed original source, not moving donor text."""
    file = ROOT / MIGRATION
    if not file.is_file() or file.is_symlink():
        raise ValueError("original ClickHouse migration file absent or redirected")
    raw = file.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if blob != PINNED_GIT_BLOB:
        raise ValueError("original ClickHouse migration source has changed")
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-tree", "HEAD", "--", MIGRATION],
        capture_output=True, text=True, input="", timeout=15, env=env, check=False,
    )
    if result.returncode != 0:
        raise ValueError("original migration Git tree unavailable")
    if result.stdout.strip() != f"100644 blob {PINNED_GIT_BLOB}\t{MIGRATION}":
        raise ValueError("original migration Git tree identity mismatch")
    return raw.decode("utf-8")


def local_only_schema_slice(source: str) -> str:
    """Adapt only the known pinned SQL table's DB/name/replicated engine.

    This must never be fed to Flind's production ClickHouse migration runner.
    """
    anchor = 'LOGS_VOLUME_BUCKETS_TABLE_SQL = f"""'
    if source.count(anchor) != 1:
        raise ValueError("original table SQL anchor missing or ambiguous")
    part = source.split(anchor, 1)[1]
    if '"""' not in part:
        raise ValueError("original table SQL boundary missing")
    sql = part.split('"""', 1)[0]
    substitutes = (
        ("{settings.CLICKHOUSE_LOGS_CLUSTER_DATABASE}", DATABASE),
        ("{TABLE_NAME}", TABLE),
        ("{MergeTreeEngine(TABLE_NAME, replication_scheme=ReplicationScheme.REPLICATED)}",
         "MergeTree"),
    )
    for original, _replacement in substitutes:
        if sql.count(original) != 1:
            raise ValueError("original ClickHouse SQL placeholder has changed")
    for original, replacement in substitutes:
        sql = sql.replace(original, replacement)
    if ("{" in sql or "}" in sql or
            "CODEC(DoubleDelta, ZSTD(1))" not in sql or
            "TTL time_bucket + INTERVAL 42 DAY" not in sql or
            "ORDER BY (team_id, time_bucket, generation, service_name, namespace, environment, severity_text)" not in sql):
        raise ValueError("source-derived ClickHouse SQL no longer matches pinned schema")
    if not sql.strip().startswith(f"CREATE TABLE IF NOT EXISTS {DATABASE}.{TABLE}"):
        raise ValueError("unexpected local-only table destination")
    return sql.strip()


class NativeLocalClickHouseSchemaSlice(unittest.TestCase):
    def test_original_schema_git_blob_is_pinned(self):
        source = original_source()
        self.assertIn("LOGS_VOLUME_BUCKETS_TABLE_SQL", source)
        self.assertIn("run_sql_with_exceptions", source)

    def test_schema_slice_rejects_missing_ddl_and_extra_placeholders(self):
        source = original_source()
        for mutated in (
            source.replace("LOGS_VOLUME_BUCKETS_TABLE_SQL = f", "MISSING_SOURCE = f", 1),
            source.replace("TTL time_bucket + INTERVAL 42 DAY", "TTL time_bucket + INTERVAL 7 DAY", 1),
            source.replace(
                "ReplicationScheme.REPLICATED", "ReplicationScheme.SHARDED", 1
            ),
        ):
            with self.subTest(mutated=hashlib.sha256(mutated.encode()).hexdigest()[:8]):
                with self.assertRaises(ValueError):
                    local_only_schema_slice(mutated)

    def test_mac_native_schema_slice_insert_idempotence_and_cleanup(self):
        if sys.platform != "darwin":
            self.skipTest("native Mac ClickHouse local binary qualification only")
        if not CH_BINARY.is_file():
            self.skipTest("Mac ClickHouse local binary not installed")
        if shutil.disk_usage("/private/tmp").free < MIN_DISK_FREE:
            self.skipTest("not enough free disk to preserve Flind Mac reserve")
        sql = local_only_schema_slice(original_source())
        queries = (
            ("create_database", f"CREATE DATABASE {DATABASE}", None),
            ("create_table", sql, None),
            ("idempotent_create", sql, None),
            ("insert",
             f"INSERT INTO {DATABASE}.{TABLE} "
             "(team_id,time_bucket,generation,service_name,namespace,environment,severity_text,log_count) "
             "VALUES (101,now(),1,'synthetic-a','isolated','test','INFO',5), "
             "(202,now(),1,'synthetic-b','isolated','test','ERROR',7)", None),
            ("read",
             f"SELECT count(), uniqExact(team_id), sum(log_count) FROM {DATABASE}.{TABLE}",
             "2\t2\t12"),
            ("drop_table", f"DROP TABLE {DATABASE}.{TABLE}", None),
            ("verify_drop",
             f"SELECT count() FROM system.tables WHERE database='{DATABASE}' AND name='{TABLE}'",
             "0"),
            ("drop_db", f"DROP DATABASE {DATABASE}", None),
            ("verify_drop_db",
             f"SELECT count() FROM system.databases WHERE name='{DATABASE}'", "0"),
        )
        with tempfile.TemporaryDirectory(prefix="flind-wave248-ch-local-", dir="/private/tmp") as directory:
            scratch = Path(directory)
            marker = scratch / ".flind-native-local-ch-v1"
            marker.write_text(MARKER, encoding="utf-8")
            path = scratch / "data"
            path.mkdir()
            self.assertEqual(marker.read_text(encoding="utf-8"), MARKER)
            env = {"HOME": str(scratch), "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
                   "LANG": "C", "TZ": "UTC"}
            for label, query, expected in queries:
                with self.subTest(operation=label):
                    self.assertGreaterEqual(shutil.disk_usage("/private/tmp").free, 15 * 1024**3,
                                            "Flind Mac disk reserve exhausted during test")
                    try:
                        result = subprocess.run(
                            [str(CH_BINARY), "local", "--path", str(path),
                             "--max_threads=2", f"--max_memory_usage={MAX_MEMORY_BYTES}",
                             "--query", query],
                            input="", capture_output=True, text=True, timeout=16, env=env,
                            check=False,
                        )
                    except subprocess.TimeoutExpired as error:
                        self.fail(f"{label}: isolated ClickHouse local step timed out: {type(error).__name__}")
                    self.assertEqual(result.returncode, 0, f"{label}: {result.stderr[-500:]}")
                    if expected is not None:
                        self.assertEqual(result.stdout.strip(), expected, label)
        # The TemporaryDirectory deletes only its newly created synthetic path.


if __name__ == "__main__":
    unittest.main()
