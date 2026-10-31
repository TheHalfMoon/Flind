"""Source-only safety contract for 0044/0045 session-replay SQL factories.

Unlike a real ClickHouse qualification, this never imports application modules,
opens a database, uses a network connection, or changes application source.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
import unittest

HELPER = (
    Path(__file__).resolve().parents[2]
    / "posthog/session_recordings/sql/session_replay_event_migrations_sql.py"
)
HELPER_BLOB = "b44c6b9fa3bccf21b860bf527842f29b3e189d9f"
TEMPLATES = {
    "ALTER_SESSION_REPLAY_ADD_CONSOLE_COLUMNS": (
        "console_log_count",
        "console_warn_count",
        "console_error_count",
    ),
    "ALTER_SESSION_REPLAY_ADD_SIZE_COLUMN": ("size",),
}
FACTORIES = {
    "ADD_CONSOLE_COUNTS_DISTRIBUTED_SESSION_REPLAY_EVENTS_TABLE_SQL": (
        "ALTER_SESSION_REPLAY_ADD_CONSOLE_COLUMNS", "distributed"
    ),
    "ADD_CONSOLE_COUNTS_WRITABLE_SESSION_REPLAY_EVENTS_TABLE_SQL": (
        "ALTER_SESSION_REPLAY_ADD_CONSOLE_COLUMNS", "writable"
    ),
    "ADD_CONSOLE_COUNTS_SESSION_REPLAY_EVENTS_TABLE_SQL": (
        "ALTER_SESSION_REPLAY_ADD_CONSOLE_COLUMNS", "sharded"
    ),
    "ADD_SIZE_DISTRIBUTED_SESSION_REPLAY_EVENTS_TABLE_SQL": (
        "ALTER_SESSION_REPLAY_ADD_SIZE_COLUMN", "distributed"
    ),
    "ADD_SIZE_WRITABLE_SESSION_REPLAY_EVENTS_TABLE_SQL": (
        "ALTER_SESSION_REPLAY_ADD_SIZE_COLUMN", "writable"
    ),
    "ADD_SIZE_SESSION_REPLAY_EVENTS_TABLE_SQL": (
        "ALTER_SESSION_REPLAY_ADD_SIZE_COLUMN", "sharded"
    ),
}


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def _single_assignments(tree: ast.Module) -> dict[str, ast.expr]:
    """Collect only unique single-target module assignments; fail on ambiguity."""
    found: dict[str, ast.expr] = {}
    sought = set(TEMPLATES) | set(FACTORIES)
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            if any(t in sought for t in targets):
                if len(stmt.targets) != 1 or len(targets) != 1:
                    raise ValueError("ambiguous SQL factory/template assignment")
                if targets[0] in found:
                    raise ValueError("duplicate SQL factory/template assignment")
                found[targets[0]] = stmt.value
        elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)) and isinstance(stmt.target, ast.Name):
            if stmt.target.id in sought:
                raise ValueError("unsupported alternate SQL assignment")
    if set(found) != sought:
        raise ValueError(f"missing SQL definitions: {sorted(sought - set(found))}")
    return found


def _factory_target(expr: ast.expr) -> str:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        if expr.value == "session_replay_events":
            return "distributed"
        if expr.value == "writable_session_replay_events":
            return "writable"
        raise ValueError("unexpected hard-coded target table")
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "SESSION_REPLAY_EVENTS_DATA_TABLE"
        and not expr.args
        and not expr.keywords
    ):
        return "sharded"
    raise ValueError("unexpected/dynamic target table")


def verify_sql_factories(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    found = _single_assignments(tree)

    for name, columns in TEMPLATES.items():
        node = found[name]
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            raise ValueError("SQL template must be literal")
        expected = (
            "ALTER TABLE {table_name} on CLUSTER '{cluster}' "
            + ", ".join(
                f"ADD COLUMN IF NOT EXISTS {col} SimpleAggregateFunction(sum, Int64)"
                for col in columns
            )
        )
        if re.sub(r"\s+", " ", node.value.strip()) != expected:
            raise ValueError(f"unsafe or unexpected SQL template: {name}")

    confirmed = []
    for name, (template, target) in FACTORIES.items():
        node = found[name]
        if not isinstance(node, ast.Lambda) or node.args.args or node.args.vararg or node.args.kwarg:
            raise ValueError(f"unexpected factory callable: {name}")
        body = node.body
        if not (
            isinstance(body, ast.Call)
            and isinstance(body.func, ast.Attribute)
            and isinstance(body.func.value, ast.Name)
            and body.func.value.id == template
            and body.func.attr == "format"
            and not body.args
        ):
            raise ValueError(f"unexpected SQL template call: {name}")
        if len(body.keywords) != 2 or {kw.arg for kw in body.keywords} != {"table_name", "cluster"}:
            raise ValueError(f"unexpected SQL factory substitution: {name}")
        kwargs = {kw.arg: kw.value for kw in body.keywords}
        cluster = kwargs["cluster"]
        if not (
            isinstance(cluster, ast.Attribute)
            and isinstance(cluster.value, ast.Name)
            and cluster.value.id == "settings"
            and cluster.attr == "CLICKHOUSE_CLUSTER"
        ):
            raise ValueError(f"SQL source must use declared cluster: {name}")
        if _factory_target(kwargs["table_name"]) != target:
            raise ValueError(f"incorrect factory target table: {name}")
        confirmed.append(name)
    return tuple(confirmed)


class ReplayConsoleAndSizeFactoryContract(unittest.TestCase):
    def test_original_blob_and_six_factories(self) -> None:
        content = HELPER.read_bytes()
        self.assertEqual(git_blob_sha(content), HELPER_BLOB)
        self.assertEqual(verify_sql_factories(content.decode("utf-8")), tuple(FACTORIES))

    def test_reject_wrong_aggregate_type(self) -> None:
        source = HELPER.read_text()
        with self.assertRaises(ValueError):
            verify_sql_factories(source.replace("SimpleAggregateFunction(sum, Int64)", "UInt64", 1))

    def test_reject_lost_if_not_exists(self) -> None:
        source = HELPER.read_text()
        with self.assertRaises(ValueError):
            verify_sql_factories(source.replace("ADD COLUMN IF NOT EXISTS size", "ADD COLUMN size", 1))

    def test_reject_wrong_table_target(self) -> None:
        source = HELPER.read_text()
        with self.assertRaises(ValueError):
            verify_sql_factories(source.replace('table_name="writable_session_replay_events"', 'table_name="events"', 1))

    def test_reject_duplicate_factory(self) -> None:
        source = HELPER.read_text()
        with self.assertRaises(ValueError):
            verify_sql_factories(source + "\nADD_SIZE_WRITABLE_SESSION_REPLAY_EVENTS_TABLE_SQL = 5\n")

    def test_reject_wrong_cluster_binding(self) -> None:
        source = HELPER.read_text()
        with self.assertRaises(ValueError):
            verify_sql_factories(source.replace("cluster=settings.CLICKHOUSE_CLUSTER", "cluster='remote'", 1))

    def test_reject_dynamic_sql_factory(self) -> None:
        source = HELPER.read_text()
        with self.assertRaises(ValueError):
            verify_sql_factories(source.replace(
                "ADD_SIZE_SESSION_REPLAY_EVENTS_TABLE_SQL = lambda: ALTER_SESSION_REPLAY_ADD_SIZE_COLUMN.format(",
                "ADD_SIZE_SESSION_REPLAY_EVENTS_TABLE_SQL = lambda: dangerous_function(",
                1,
            ))

    def test_reject_missing_aggregate_column(self) -> None:
        source = HELPER.read_text()
        with self.assertRaises(ValueError):
            verify_sql_factories(source.replace(
                "ADD COLUMN IF NOT EXISTS console_error_count SimpleAggregateFunction(sum, Int64)",
                "ADD COLUMN IF NOT EXISTS console_typo_count SimpleAggregateFunction(sum, Int64)", 1,
            ))


if __name__ == "__main__":
    unittest.main()
