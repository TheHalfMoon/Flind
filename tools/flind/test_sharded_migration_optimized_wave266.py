"""First-party optimized-Python regression for original sharded migration routing.

Executes the exact original function body with synthetic cluster doubles; no DB access.
"""
from __future__ import annotations

import ast
from enum import Enum
from pathlib import Path
import subprocess
from types import SimpleNamespace
from typing import Optional
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "posthog/clickhouse/client/migration_tools.py"
EXPECTED_BLOB = "17a082e56f6c2825279e8337d1572be921b0aeac"


class NodeRole(Enum):
    DATA = 1
    INGESTION_SMALL = 2
    SATELLITE = 3
    ALL = 4


class SyntheticCluster:
    def __init__(self):
        self.shard_calls = 0
        self.satellite_calls = 0

    def map_one_host_per_shard(self, query):
        self.shard_calls += 1
        return SimpleNamespace(result=lambda: None)

    def any_host_by_roles(self, query, node_roles):
        self.satellite_calls += 1
        return SimpleNamespace(result=lambda: None)


def original_function(cluster, local=False):
    source_blob = subprocess.check_output(["git", "hash-object", str(SOURCE)], text=True).strip()
    if source_blob != EXPECTED_BLOB:
        raise RuntimeError(f"Original migration routing source changed: {source_blob}")
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    function = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "run_sql_with_exceptions"
    )
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    namespace = {
        "NodeRole": NodeRole,
        "Optional": Optional,
        "migrations": SimpleNamespace(RunPython=lambda fn: SimpleNamespace(_func=fn)),
        "DATA_NODE_ROLES": {NodeRole.DATA, NodeRole.SATELLITE},
        "SINGLE_SHARD_DATA_NODE_ROLES": {NodeRole.SATELLITE},
        "collapses_to_all_nodes": lambda: local,
        "get_migrations_cluster": lambda: cluster,
        "Query": lambda sql: sql,
        "logger": SimpleNamespace(info=lambda *args: None),
    }
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["run_sql_with_exceptions"]


class ShardedRoutingOptimizedTests(unittest.TestCase):
    def _execute(self, role, local=False):
        cluster = SyntheticCluster()
        operation = original_function(cluster, local=local)(
            "ALTER TABLE synthetic ADD COLUMN x UInt8",
            node_roles=[role],
            sharded=True,
            is_alter_on_replicated_table=True,
        )
        return cluster, operation

    def test_foreign_non_data_role_fails_closed_before_query(self):
        cluster, operation = self._execute(NodeRole.INGESTION_SMALL)
        with self.assertRaisesRegex(AssertionError, "node_roles must be exactly one"):
            operation._func(None)
        self.assertEqual(cluster.shard_calls, 0)
        self.assertEqual(cluster.satellite_calls, 0)

    def test_data_role_routes_once(self):
        cluster, operation = self._execute(NodeRole.DATA)
        operation._func(None)
        self.assertEqual(cluster.shard_calls, 1)
        self.assertEqual(cluster.satellite_calls, 0)

    def test_satellite_role_routes_to_satellite(self):
        cluster, operation = self._execute(NodeRole.SATELLITE)
        operation._func(None)
        self.assertEqual(cluster.shard_calls, 0)
        self.assertEqual(cluster.satellite_calls, 1)

    def test_local_mode_preserves_collapsed_routing(self):
        cluster, operation = self._execute(NodeRole.INGESTION_SMALL, local=True)
        operation._func(None)
        self.assertEqual(cluster.shard_calls, 1)
        self.assertEqual(cluster.satellite_calls, 0)


if __name__ == "__main__":
    unittest.main()
