"""Fail-closed, source-only guard for original ClickHouse migration 0047.

Checks SQL/table coverage and Kafka/MV safety ordering without importing Django,
connecting to services, or claiming a live migration qualification.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
import unittest


SOURCE_FILE = (
    Path(__file__).resolve().parents[2]
    / "posthog/clickhouse/migrations/0047_add_insertion_timestamp_to_events.py"
)
SOURCE_BLOB = "9fca4962340da796d6120d1ca437e14240ceb97a"
TARGET_TABLES = ("events", "writable_events", "sharded_events")
EXPECTED_SQL = (
    "ALTER TABLE {table} ON CLUSTER '{cluster}' "
    "ADD COLUMN IF NOT EXISTS inserted_at Nullable(DateTime64(6, 'UTC')) DEFAULT NULL"
)
EXPECTED_STEPS = (
    "drop:events_json_mv",
    "drop:kafka_events_json",
    "add_inserted_at:events,writable_events,sharded_events",
    "create:kafka_events_json",
    "create:events_json_mv",
)


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def _named_call(expr: ast.AST, name: str) -> ast.Call:
    if not (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name)):
        raise ValueError(f"expected explicit call {name}")
    if expr.func.id != name or expr.keywords:
        raise ValueError(f"unexpected call instead of {name}")
    return expr


def _source_contract(source: str) -> tuple[str, ...]:
    """Parse without executing the source and reject any unexpected op shape."""
    tree = ast.parse(source)
    allowed = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign)
    if any(not isinstance(stmt, allowed) for stmt in tree.body):
        raise ValueError("unexpected top-level executable statement")

    assignments: dict[str, ast.AST] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                raise ValueError("unexpected assignment target")
            name = stmt.targets[0].id
            if name in assignments:
                raise ValueError("duplicate source assignment")
            assignments[name] = stmt.value
    if set(assignments) != {"ADD_COLUMNS_BASE_SQL", "operations"}:
        raise ValueError("unexpected global assignments")

    sql_node = assignments["ADD_COLUMNS_BASE_SQL"]
    if not isinstance(sql_node, ast.Constant) or not isinstance(sql_node.value, str):
        raise ValueError("SQL must be a string literal")
    sql = re.sub(r"\s+", " ", sql_node.value.strip())
    if sql != EXPECTED_SQL:
        raise ValueError("inserted_at DDL changed, no longer safe or complete")

    funcs = [stmt for stmt in tree.body if isinstance(stmt, ast.FunctionDef)]
    if len(funcs) != 1 or funcs[0].name != "add_columns_to_required_tables":
        raise ValueError("unexpected Python migration function")
    fn = funcs[0]
    if len(fn.args.args) != 1 or len(fn.body) != 3:
        raise ValueError("unexpected Python migration body/args")
    tables: list[str] = []
    for statement in fn.body:
        if not isinstance(statement, ast.Expr):
            raise ValueError("unexpected function statement")
        outer = _named_call(statement.value, "sync_execute")
        if len(outer.args) != 1:
            raise ValueError("sync_execute args changed")
        fmt = outer.args[0]
        if not (
            isinstance(fmt, ast.Call)
            and isinstance(fmt.func, ast.Attribute)
            and fmt.func.attr == "format"
            and isinstance(fmt.func.value, ast.Name)
            and fmt.func.value.id == "ADD_COLUMNS_BASE_SQL"
            and not fmt.args
        ):
            raise ValueError("not the source-locked DDL template")
        kwargs = {k.arg: k.value for k in fmt.keywords}
        if set(kwargs) != {"table", "cluster"}:
            raise ValueError("missing/extra DDL template keyword")
        if not (isinstance(kwargs["table"], ast.Constant) and isinstance(kwargs["table"].value, str)):
            raise ValueError("table must be literal")
        if not (isinstance(kwargs["cluster"], ast.Name) and kwargs["cluster"].id == "CLICKHOUSE_CLUSTER"):
            raise ValueError("wrong DDL target cluster")
        tables.append(kwargs["table"].value)
    if tuple(tables) != TARGET_TABLES:
        raise ValueError("inserted_at table coverage/order changed")

    ops = assignments["operations"]
    if not isinstance(ops, ast.List) or len(ops.elts) != 5:
        raise ValueError("unexpected migration operations")

    def wrapped(expr: ast.AST) -> ast.AST:
        call = _named_call(expr, "run_sql_with_exceptions")
        if len(call.args) != 1:
            raise ValueError("wrong SQL wrapper arity")
        return call.args[0]

    def drop(expr: ast.AST, table: str) -> None:
        inner = wrapped(expr)
        if not (isinstance(inner, ast.JoinedStr) and len(inner.values) == 3):
            raise ValueError("DROP must use one source cluster placeholder")
        a, b, c = inner.values
        if not (
            isinstance(a, ast.Constant) and a.value == f"DROP TABLE IF EXISTS {table} ON CLUSTER '"
            and isinstance(b, ast.FormattedValue)
            and isinstance(b.value, ast.Name) and b.value.id == "CLICKHOUSE_CLUSTER"
            and b.format_spec is None
            and isinstance(c, ast.Constant) and c.value == "'"
        ):
            raise ValueError("DROP table, IF EXISTS or cluster changed")

    def create(expr: ast.AST, factory: str) -> None:
        inner = wrapped(expr)
        call = _named_call(inner, factory)
        if call.args:
            raise ValueError("unexpected CREATE factory arguments")

    drop(ops.elts[0], "events_json_mv")
    drop(ops.elts[1], "kafka_events_json")
    python_op = ops.elts[2]
    if not (
        isinstance(python_op, ast.Call)
        and isinstance(python_op.func, ast.Attribute)
        and isinstance(python_op.func.value, ast.Name)
        and python_op.func.value.id == "migrations"
        and python_op.func.attr == "RunPython"
        and len(python_op.args) == 1
        and isinstance(python_op.args[0], ast.Name)
        and python_op.args[0].id == "add_columns_to_required_tables"
        and not python_op.keywords
    ):
        raise ValueError("Python migration step/order changed")
    create(ops.elts[3], "KAFKA_EVENTS_TABLE_JSON_SQL")
    create(ops.elts[4], "EVENTS_TABLE_JSON_MV_SQL")
    return EXPECTED_STEPS


class Migration0047SourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_bytes = SOURCE_FILE.read_bytes()
        cls.original = cls.original_bytes.decode("utf-8")

    def test_pinned_git_blob(self) -> None:
        self.assertEqual(git_blob_sha(self.original_bytes), SOURCE_BLOB)

    def test_complete_ordered_operations_and_all_three_columns(self) -> None:
        self.assertEqual(_source_contract(self.original), EXPECTED_STEPS)

    def test_reject_missing_or_misdirected_column(self) -> None:
        for edited in (
            self.original.replace('table="writable_events"', 'table="non_events"'),
            self.original.replace('table="sharded_events"', 'table="events"'),
            self.original.replace("DEFAULT NULL", "DEFAULT now()"),
            self.original.replace("DateTime64(6, 'UTC')", "String"),
        ):
            with self.subTest(edited=edited[-120:]):
                with self.assertRaises(ValueError):
                    _source_contract(edited)

    def test_reject_unsafe_drop_and_recreation_order(self) -> None:
        old = 'run_sql_with_exceptions(f"DROP TABLE IF EXISTS events_json_mv ON CLUSTER \'{CLICKHOUSE_CLUSTER}\'"),'
        bad = old.replace('events_json_mv', 'kafka_events_json')
        with self.assertRaises(ValueError):
            _source_contract(self.original.replace(old, bad))
        with self.assertRaises(ValueError):
            _source_contract(self.original.replace("EVENTS_TABLE_JSON_MV_SQL()),", "KAFKA_EVENTS_TABLE_JSON_SQL()),"))

    def test_reject_executable_top_level_injection(self) -> None:
        with self.assertRaises(ValueError):
            _source_contract(self.original + "\nprint('unexpected top-level side effect')\n")

    def test_reject_dynamic_operations(self) -> None:
        with self.assertRaises(ValueError):
            _source_contract(self.original.split("operations = [")[0] + "operations = build_operations()\n")


if __name__ == "__main__":
    unittest.main()
