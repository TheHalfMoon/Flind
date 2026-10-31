"""Source-only fail-closed guard for original replay migrations 0044-0046.

No Django, ClickHouse, Kafka, network, or production data is accessed.
A passing result does NOT qualify live migration application.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest


MIGRATIONS = Path(__file__).resolve().parents[2] / "posthog" / "clickhouse" / "migrations"

SOURCES = {
    "0044_session_replay_events_console_counts.py": {
        "blob": "071c18c4cbd1d7968beb9a8e4fe84b9206fe1452",
        "ordered_calls": (
            "DROP_SESSION_REPLAY_EVENTS_TABLE_MV_SQL",
            "DROP_KAFKA_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "ADD_CONSOLE_COUNTS_WRITABLE_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "ADD_CONSOLE_COUNTS_DISTRIBUTED_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "ADD_CONSOLE_COUNTS_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "KAFKA_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "SESSION_REPLAY_EVENTS_TABLE_MV_SQL",
        ),
    },
    "0045_session_replay_events_size.py": {
        "blob": "f4c04bd746f34c0899a1c7d79dc1f9f686c23570",
        "ordered_calls": (
            "DROP_SESSION_REPLAY_EVENTS_TABLE_MV_SQL",
            "DROP_KAFKA_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "ADD_SIZE_WRITABLE_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "ADD_SIZE_DISTRIBUTED_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "ADD_SIZE_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "KAFKA_SESSION_REPLAY_EVENTS_TABLE_SQL",
            "SESSION_REPLAY_EVENTS_TABLE_MV_SQL",
        ),
    },
}
NOOP_0046 = (
    "0046_ensure_kafa_session_replay_table_exists.py",
    "85d6664e475be214819289a1421246f22809b630",
)


def git_blob_sha(content: bytes) -> str:
    """Match Git's SHA-1 blob identity without requiring a Git subprocess."""
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def operations_from_source(source: str) -> tuple[str, ...]:
    """Reject dynamic operations, side-effecting calls and unexpected AST shapes."""
    tree = ast.parse(source)
    assignments = [
        item for item in tree.body
        if isinstance(item, ast.Assign)
        and len(item.targets) == 1
        and isinstance(item.targets[0], ast.Name)
        and item.targets[0].id == "operations"
    ]
    if len(assignments) != 1 or not isinstance(assignments[0].value, ast.List):
        raise ValueError("expected exactly one literal operations list")

    names = []
    for op in assignments[0].value.elts:
        if not isinstance(op, ast.Call) or not isinstance(op.func, ast.Name):
            raise ValueError("operation is not an explicit run_sql_with_exceptions call")
        if op.func.id != "run_sql_with_exceptions" or len(op.args) != 1 or op.keywords:
            raise ValueError("unexpected operation wrapper")
        inner = op.args[0]
        if not isinstance(inner, ast.Call) or not isinstance(inner.func, ast.Name):
            raise ValueError("SQL factory must be an explicit named function call")
        if inner.args or inner.keywords:
            raise ValueError("SQL factory arguments must be empty")
        names.append(inner.func.id)
    return tuple(names)


class OriginalReplaySourceContract(unittest.TestCase):
    def test_source_provenance_and_order(self) -> None:
        for filename, contract in SOURCES.items():
            with self.subTest(migration=filename):
                content = (MIGRATIONS / filename).read_bytes()
                self.assertEqual(git_blob_sha(content), contract["blob"])
                self.assertEqual(
                    operations_from_source(content.decode("utf-8")),
                    contract["ordered_calls"],
                )

    def test_original_0046_remains_noop(self) -> None:
        filename, pinned_blob = NOOP_0046
        content = (MIGRATIONS / filename).read_bytes()
        self.assertEqual(git_blob_sha(content), pinned_blob)
        tree = ast.parse(content.decode("utf-8"))
        assignments = [
            item for item in tree.body
            if isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and item.target.id == "operations"
        ]
        self.assertEqual(len(assignments), 1)
        self.assertIsInstance(assignments[0].value, ast.List)
        self.assertEqual(assignments[0].value.elts, [])

    def test_reject_reordered_operations(self) -> None:
        calls = SOURCES["0044_session_replay_events_console_counts.py"]["ordered_calls"]
        swapped = (calls[1], calls[0], *calls[2:])
        self.assertNotEqual(swapped, calls)
        source = "operations = [\n" + "".join(
            f"    run_sql_with_exceptions({name}()),\n" for name in swapped
        ) + "]\n"
        self.assertEqual(operations_from_source(source), swapped)
        self.assertNotEqual(operations_from_source(source), calls)

    def test_reject_non_literal_or_side_effecting_operations(self) -> None:
        for source in (
            "operations = build_operations()\n",
            "operations = [run_sql_with_exceptions(exec('x'))]\n",
            "operations = [run_sql_with_exceptions(FUNCTION(1))]\n",
            "operations = [run_sql_with_exceptions(FUNCTION(x=1))]\n",
        ):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    operations_from_source(source)


if __name__ == "__main__":
    unittest.main()
