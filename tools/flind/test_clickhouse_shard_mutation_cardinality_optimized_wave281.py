"""Isolated original MutationRunner.enqueue_on_shards cardinality regression under -O.

Runs the exact method extracted from the Git source, with synthetic cluster results.
No network, database, Kafka, or shared service is required.
"""

from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path
from typing import NamedTuple

SOURCE = (
    Path(os.environ["FLIND_CLUSTER_SOURCE"])
    if "FLIND_CLUSTER_SOURCE" in os.environ
    else Path(__file__).resolve().parents[2] / "posthog/clickhouse/cluster.py"
)


class Host(NamedTuple):
    shard_num: int | None
    name: str


class FakeMap:
    def __init__(self, pairs):
        self.pairs = pairs

    def result(self):
        return self.pairs

    def __len__(self):
        return len(self.pairs)


class FakeCluster:
    def __init__(self, pairs):
        self.mapping = FakeMap(pairs)
        self.mode = None

    def map_one_host_per_shard(self, runner):
        self.mode = "all"
        return self.mapping

    def map_any_host_in_shards(self, mapping):
        self.mode = "selected"
        self.requested = mapping
        return self.mapping


def original_runner():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MutationRunner"]
    if len(classes) != 1:
        raise RuntimeError("original MutationRunner missing or ambiguous")
    methods = [
        node for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "enqueue_on_shards"
    ]
    if len(methods) != 1 or not isinstance(methods[0], ast.FunctionDef):
        raise RuntimeError("original enqueue_on_shards missing or ambiguous")
    isolated = ast.parse("class IsolatedRunner: pass").body[0]
    isolated.body = [methods[0]]
    module = ast.Module(
        body=[
            ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
            isolated,
        ],
        type_ignores=[],
    )
    namespace = {}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)  # noqa: S102 - isolated original method
    return namespace["IsolatedRunner"]()


class ShardMutationCardinalityTests(unittest.TestCase):
    def setUp(self):
        self.runner = original_runner()

    def test_unique_shards_preserve_results(self):
        cluster = FakeCluster({Host(1, "a"): "first", Host(2, "b"): "second"})
        self.assertEqual(self.runner.enqueue_on_shards(cluster), {1: "first", 2: "second"})
        self.assertEqual(cluster.mode, "all")

    def test_null_shard_rejected(self):
        cluster = FakeCluster({Host(None, "missing"): "synthetic"})
        with self.assertRaises(AssertionError):
            self.runner.enqueue_on_shards(cluster)

    def test_duplicate_shard_rejected(self):
        cluster = FakeCluster({Host(1, "a"): "first", Host(1, "b"): "second"})
        with self.assertRaises(AssertionError):
            self.runner.enqueue_on_shards(cluster)

    def test_mixed_valid_and_null_rejected(self):
        cluster = FakeCluster({Host(1, "a"): "first", Host(None, "missing"): "second"})
        with self.assertRaises(AssertionError):
            self.runner.enqueue_on_shards(cluster)

    def test_empty_result_is_valid(self):
        self.assertEqual(self.runner.enqueue_on_shards(FakeCluster({})), {})

    def test_explicit_shard_selection_preserved(self):
        cluster = FakeCluster({Host(3, "c"): "third"})
        self.assertEqual(self.runner.enqueue_on_shards(cluster, shards=[3, 3]), {3: "third"})
        self.assertEqual(cluster.mode, "selected")
        self.assertEqual(list(cluster.requested), [3])


if __name__ == "__main__":
    unittest.main()
