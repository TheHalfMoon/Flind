"""Isolated source-attested original ClickHouse mutation cardinality tests; no network."""

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


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.connection = SimpleNamespace(context=SimpleNamespace(server_info=object()))
        self.queries = []

    def substitute_params(self, statement, parameters, context):
        return statement

    def execute(self, statement, parameters=None):
        self.queries.append((statement, parameters))
        return self.rows


def original_find_existing_mutations():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MutationRunner"]
    if len(classes) != 1:
        raise RuntimeError("original MutationRunner missing or ambiguous")
    methods = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == "find_existing_mutations"]
    if len(methods) != 1:
        raise RuntimeError("original find_existing_mutations missing or ambiguous")
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), methods[0]],
        type_ignores=[],
    )
    namespace = {"settings": SimpleNamespace(CLICKHOUSE_DATABASE="synthetic_flind")}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)  # noqa: S102 - isolated original method
    return namespace["find_existing_mutations"]


class MutationCardinalityTests(unittest.TestCase):
    def setUp(self):
        self.find = original_find_existing_mutations()
        self.commands = {"UPDATE x = 1", "DELETE WHERE x = 2"}
        self.runner = SimpleNamespace(table="synthetic_events", parameters={}, get_all_commands=lambda: self.commands)

    def test_missing_result_row_fails_closed(self):
        client = FakeClient([("synthetic-id-1",)])
        with self.assertRaises(AssertionError):
            self.find(self.runner, client, self.commands)
        self.assertEqual(len(client.queries), 1)

    def test_excess_result_row_fails_closed(self):
        client = FakeClient([("id-1",), ("id-2",), ("id-3",)])
        with self.assertRaises(AssertionError):
            self.find(self.runner, client, self.commands)
        self.assertEqual(len(client.queries), 1)

    def test_two_result_rows_return_both_ids(self):
        result = self.find(self.runner, FakeClient([("id-1",), ("id-2",)]), self.commands)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result.values()), {"id-1", "id-2"})

    def test_none_result_row_does_not_create_false_mutation(self):
        result = self.find(self.runner, FakeClient([("id-1",), (None,)]), self.commands)
        self.assertEqual(len(result), 1)
        self.assertEqual(set(result.values()), {"id-1"})


if __name__ == "__main__":
    unittest.main()
