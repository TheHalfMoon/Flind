"""Isolated original FuturesMap guard regression; duplicate futures must fail under Python -O."""

from __future__ import annotations

import ast
import os
import unittest
from concurrent.futures import Future, TimeoutError, as_completed
from pathlib import Path

SOURCE = (
    Path(os.environ["FLIND_CLUSTER_SOURCE"])
    if "FLIND_CLUSTER_SOURCE" in os.environ
    else Path(__file__).resolve().parents[2] / "posthog/clickhouse/cluster.py"
)


def original_as_completed():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FuturesMap"
    ]
    if len(classes) != 1:
        raise RuntimeError("original FuturesMap missing or ambiguous")
    methods = [
        node for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == "as_completed"
    ]
    if len(methods) != 1:
        raise RuntimeError("original FuturesMap.as_completed missing or ambiguous")
    isolated_class = ast.parse("class IsolatedFuturesMap(dict): pass").body[0]
    isolated_class.body = [methods[0]]
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__", names=[ast.alias(name="annotations")], level=0
            ),
            isolated_class,
        ],
        type_ignores=[],
    )
    namespace = {"as_completed": as_completed}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)  # noqa: S102 - isolated original method

    def run(mapping, timeout=None):
        return namespace["IsolatedFuturesMap"](mapping).as_completed(timeout=timeout)

    return run


def finished(value):
    future = Future()
    future.set_result(value)
    return future


class FuturesMapGuardTests(unittest.TestCase):
    def setUp(self):
        self.method = original_as_completed()

    def test_duplicate_future_rejected_before_yield(self):
        shared = finished(1)
        with self.assertRaises(AssertionError):
            list(self.method({"host-a": shared, "host-b": shared}))

    def test_duplicate_failed_future_rejected_before_yield(self):
        shared = Future()
        shared.set_exception(ValueError("synthetic"))
        with self.assertRaises(AssertionError):
            list(self.method({"host-a": shared, "host-b": shared}))

    def test_unique_futures_keep_host_mapping(self):
        first, second = finished(1), finished(2)
        pairs = list(self.method({"host-a": first, "host-b": second}))
        self.assertEqual(dict(pairs), {"host-a": first, "host-b": second})

    def test_empty_mapping(self):
        self.assertEqual(list(self.method({})), [])

    def test_timeout_is_propagated(self):
        pending = Future()
        with self.assertRaises(TimeoutError):
            list(self.method({"host-a": pending}, timeout=0))


if __name__ == "__main__":
    unittest.main()
