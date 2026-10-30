"""Isolated original HogQL lazy-join chain guard regression under Python -O.

AST-extracts the actual source method, preserving its implementation. Synthetic
visitor/AST doubles; no database, network, customer data or full Django bootstrap.
"""
from __future__ import annotations

import ast as py_ast
import os
import types
import unittest
from pathlib import Path

SOURCE = Path(
    os.environ.get(
        "FLIND_LAZY_SOURCE",
        str(Path(__file__).resolve().parents[2] / "posthog/hogql/transforms/lazy_tables.py"),
    )
)


class FakeCloningVisitor:
    def __init__(self, **kwargs):
        self.options = kwargs

    def visit_call(self, node):
        return ("fallback", node)


class FakeFinder:
    def __init__(self, ids):
        self.ids = ids
        self.found = []

    def visit(self, node):
        self.found = node.found


class FakeField:
    def __init__(self, chain, type=None):
        self.chain = chain
        self.type = type


class FakeFieldType:
    def __init__(self, name, table_type):
        self.name = name
        self.table_type = table_type


FAKE_AST = types.SimpleNamespace(Field=FakeField, FieldType=FakeFieldType)


def original_replacer():
    source = SOURCE.read_text(encoding="utf-8")
    tree = py_ast.parse(source, filename=str(SOURCE))
    classes = [
        node
        for node in tree.body
        if isinstance(node, py_ast.ClassDef) and node.name == "LazyJoinExpressionReplacer"
    ]
    if len(classes) != 1:
        raise RuntimeError("Original LazyJoinExpressionReplacer missing or ambiguous")
    methods = [
        node
        for node in classes[0].body
        if isinstance(node, py_ast.FunctionDef) and node.name in {"__init__", "visit_call"}
    ]
    if len(methods) != 2 or {m.name for m in methods} != {"__init__", "visit_call"}:
        raise RuntimeError("Original lazy join methods missing or ambiguous")
    isolated = py_ast.ClassDef(
        name="IsolatedReplacer",
        bases=[py_ast.Name(id="CloningVisitor", ctx=py_ast.Load())],
        keywords=[],
        body=methods,
        decorator_list=[],
    )
    module = py_ast.Module(
        body=[
            py_ast.ImportFrom(
                module="__future__", names=[py_ast.alias(name="annotations")], level=0
            ),
            isolated,
        ],
        type_ignores=[],
    )
    namespace = {
        "CloningVisitor": FakeCloningVisitor,
        "LazyJoinFieldFinder": FakeFinder,
        "ast": FAKE_AST,
    }
    exec(compile(py_ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)  # noqa: S102
    return namespace["IsolatedReplacer"]("synthetic_alias", "synthetic_type", {17})


class LazyJoinChainTests(unittest.TestCase):
    def call(self, chains, *, name="if", has_second=True):
        arg = types.SimpleNamespace(found=[FakeField(chain) for chain in chains])
        args = [object(), arg] if has_second else [object()]
        node = types.SimpleNamespace(name=name, args=args)
        return original_replacer().visit_call(node)

    def test_exactly_two_components_rewritten(self):
        field = self.call([["lazy", "column"]])
        self.assertIsInstance(field, FakeField)
        self.assertEqual(field.chain, ["synthetic_alias", "column"])
        self.assertEqual(field.type.name, "column")
        self.assertEqual(field.type.table_type, "synthetic_type")

    def test_too_long_chain_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Expected lazy join field chain"):
            self.call([["lazy", "column", "nested"]])

    def test_too_short_chain_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Expected lazy join field chain"):
            self.call([["lazy"]])

    def test_empty_chain_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Expected lazy join field chain"):
            self.call([[]])

    def test_no_lazy_field_preserves_fallback(self):
        self.assertEqual(self.call([])[0], "fallback")

    def test_non_if_call_preserves_fallback(self):
        self.assertEqual(self.call([["lazy", "column", "nested"]], name="other")[0], "fallback")

    def test_if_without_second_arg_preserves_fallback(self):
        self.assertEqual(
            self.call([["lazy", "column", "nested"]], has_second=False)[0], "fallback"
        )


if __name__ == "__main__":
    unittest.main()
