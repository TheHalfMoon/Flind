"""Isolated original ClickHouse MutationWaiter regression: duplicate statuses fail closed under -O."""

from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

SOURCE = (
    Path(os.environ["FLIND_CLUSTER_SOURCE"])
    if "FLIND_CLUSTER_SOURCE" in os.environ
    else Path(__file__).resolve().parents[2] / "posthog/clickhouse/cluster.py"
)


class MutationNotFound(Exception):
    pass


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def execute(self, query, parameters=None):
        self.queries.append((query, parameters))
        return self.rows


def original_is_done():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MutationWaiter"
    ]
    if len(classes) != 1:
        raise RuntimeError("original MutationWaiter missing or ambiguous")
    methods = [
        node
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == "is_done"
    ]
    if len(methods) != 1:
        raise RuntimeError("original MutationWaiter.is_done missing or ambiguous")
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__", names=[ast.alias(name="annotations")], level=0
            ),
            methods[0],
        ],
        type_ignores=[],
    )
    namespace = {
        "settings": SimpleNamespace(CLICKHOUSE_DATABASE="synthetic_flind"),
        "MutationNotFound": MutationNotFound,
    }
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)  # noqa: S102 - isolated original method
    return namespace["is_done"]


class MutationStatusCardinalityTests(unittest.TestCase):
    def setUp(self):
        self.is_done = original_is_done()
        self.waiter = SimpleNamespace(
            table="synthetic_events", mutation_ids={"id-1", "id-2"}
        )

    def test_duplicate_conflicting_status_fails_closed(self):
        client = FakeClient([("id-1", False), ("id-1", True), ("id-2", True)])
        with self.assertRaises(AssertionError):
            self.is_done(self.waiter, client)
        self.assertEqual(len(client.queries), 1)

    def test_duplicate_completed_status_fails_closed(self):
        client = FakeClient([("id-1", True), ("id-1", True), ("id-2", True)])
        with self.assertRaises(AssertionError):
            self.is_done(self.waiter, client)
        self.assertEqual(len(client.queries), 1)

    def test_unique_completed_statuses(self):
        self.assertTrue(
            self.is_done(self.waiter, FakeClient([("id-1", True), ("id-2", True)]))
        )

    def test_unique_pending_statuses(self):
        self.assertFalse(
            self.is_done(self.waiter, FakeClient([("id-1", False), ("id-2", True)]))
        )

    def test_missing_mutation_rejected(self):
        with self.assertRaises(MutationNotFound):
            self.is_done(self.waiter, FakeClient([("id-1", True)]))

    def test_unexpected_mutation_rejected(self):
        with self.assertRaises(ValueError):
            self.is_done(
                self.waiter,
                FakeClient([("id-1", True), ("id-2", True), ("id-3", True)]),
            )


if __name__ == "__main__":
    unittest.main()
