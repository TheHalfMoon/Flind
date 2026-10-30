"""Fail-closed source contract for original ClickHouse migrations 0001-0003.

Source-only: no application imports, DB connections, network, or migration
execution. This does NOT qualify a Django command or real ClickHouse schema.
"""

import ast
import unittest
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[2] / "posthog/clickhouse/migrations"
CONTRACTS = {
    "0001_initial.py": (
        {
            "posthog.clickhouse.client.connection": {"NodeRole"},
            "posthog.clickhouse.client.migration_tools": {"run_sql_with_exceptions"},
            "posthog.models.event.sql": {"EVENTS_TABLE_SQL"},
            "posthog.settings": {"CLICKHOUSE_DATABASE"},
        },
        (
            'run_sql_with_exceptions(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DATABASE}", node_roles=[NodeRole.ALL])',
            "run_sql_with_exceptions(EVENTS_TABLE_SQL())",
        ),
    ),
    "0002_events_materialized.py": (
        {"posthog.clickhouse.client.migration_tools": {"run_sql_with_exceptions"}},
        ('run_sql_with_exceptions("SELECT 1")',),
    ),
    "0003_person.py": (
        {
            "posthog.clickhouse.client.migration_tools": {"run_sql_with_exceptions"},
            "posthog.models.person.sql": {
                "COMMENT_DISTINCT_ID_COLUMN_SQL",
                "PERSONS_DISTINCT_ID_TABLE_SQL",
                "PERSONS_TABLE_SQL",
            },
        },
        (
            "run_sql_with_exceptions(PERSONS_TABLE_SQL())",
            "run_sql_with_exceptions(PERSONS_DISTINCT_ID_TABLE_SQL())",
            "run_sql_with_exceptions(COMMENT_DISTINCT_ID_COLUMN_SQL(), sharded=False, is_alter_on_replicated_table=True)",
        ),
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("FLIND_W285_MIGRATION_CONTRACT: " + message)


def validate_source(filename: str, source: str) -> int:
    require(filename in CONTRACTS, "unknown migration")
    expected_imports, expected_operations = CONTRACTS[filename]
    tree = ast.parse(source, filename=filename)
    require(len(tree.body) == len(expected_imports) + 1, "unexpected top-level statement")
    imports = {}
    for node in tree.body[:-1]:
        require(isinstance(node, ast.ImportFrom) and node.level == 0, "unexpected import")
        require(node.module not in imports, "duplicate import")
        require(all(alias.asname is None for alias in node.names), "aliased import")
        imports[node.module] = {alias.name for alias in node.names}
        require(len(imports[node.module]) == len(node.names), "duplicate imported name")
    require(imports == expected_imports, "import contract changed")
    assignment = tree.body[-1]
    require(isinstance(assignment, ast.Assign), "operations must be a direct assignment")
    require(len(assignment.targets) == 1 and isinstance(assignment.targets[0], ast.Name)
            and assignment.targets[0].id == "operations", "unexpected operations target")
    require(isinstance(assignment.value, ast.List), "operations must be a literal ordered list")
    actual = assignment.value.elts
    require(len(actual) == len(expected_operations), "operation count changed")
    for index, (node, expression) in enumerate(zip(actual, expected_operations), start=1):
        expected = ast.parse(expression, mode="eval").body
        require(ast.dump(node, include_attributes=False) == ast.dump(expected, include_attributes=False),
                f"operation {index} changed")
    return len(actual)


class OriginalEarlyClickHouseMigrationSourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {name: (MIGRATIONS / name).read_text(encoding="utf-8") for name in CONTRACTS}

    def mutate(self, filename: str, old: str, new: str) -> str:
        source = self.sources[filename]
        self.assertIn(old, source)
        changed = source.replace(old, new, 1)
        self.assertNotEqual(source, changed)
        return changed

    def test_original_sources_exact_operations(self):
        self.assertEqual({name: validate_source(name, source) for name, source in self.sources.items()},
                         {"0001_initial.py": 2, "0002_events_materialized.py": 1, "0003_person.py": 3})

    def test_0001_database_role_must_remain_all(self):
        source = self.mutate("0001_initial.py", "node_roles=[NodeRole.ALL]", "node_roles=[]")
        with self.assertRaisesRegex(RuntimeError, "operation 1"):
            validate_source("0001_initial.py", source)

    def test_0001_database_sql_must_not_change(self):
        source = self.mutate("0001_initial.py", "CREATE DATABASE IF NOT EXISTS", "DROP DATABASE IF EXISTS")
        with self.assertRaisesRegex(RuntimeError, "operation 1"):
            validate_source("0001_initial.py", source)

    def test_0002_sentinel_must_remain_nonmutating(self):
        source = self.mutate("0002_events_materialized.py", "SELECT 1", "DROP TABLE events")
        with self.assertRaisesRegex(RuntimeError, "operation 1"):
            validate_source("0002_events_materialized.py", source)

    def test_0002_extra_operation_rejected(self):
        source = self.mutate("0002_events_materialized.py", '"SELECT 1")]', '"SELECT 1"), run_sql_with_exceptions("SELECT 2")]')
        with self.assertRaisesRegex(RuntimeError, "operation count"):
            validate_source("0002_events_materialized.py", source)

    def test_0003_person_order_must_remain_stable(self):
        source = self.mutate("0003_person.py", "PERSONS_TABLE_SQL()", "PERSONS_DISTINCT_ID_TABLE_SQL()")
        with self.assertRaisesRegex(RuntimeError, "operation 1"):
            validate_source("0003_person.py", source)

    def test_0003_sharding_flags_must_remain_explicit(self):
        source = self.mutate("0003_person.py", "sharded=False", "sharded=True")
        with self.assertRaisesRegex(RuntimeError, "operation 3"):
            validate_source("0003_person.py", source)

    def test_0003_replication_flag_must_remain_explicit(self):
        source = self.mutate("0003_person.py", "is_alter_on_replicated_table=True", "is_alter_on_replicated_table=False")
        with self.assertRaisesRegex(RuntimeError, "operation 3"):
            validate_source("0003_person.py", source)

    def test_unexpected_top_level_side_effect_rejected(self):
        source = self.sources["0003_person.py"] + "\nprint('unexpected')\n"
        with self.assertRaisesRegex(RuntimeError, "unexpected top-level"):
            validate_source("0003_person.py", source)

    def test_import_alias_rejected(self):
        source = self.mutate("0001_initial.py", "import NodeRole", "import NodeRole as other")
        with self.assertRaisesRegex(RuntimeError, "aliased import"):
            validate_source("0001_initial.py", source)

    def test_unknown_migration_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "unknown migration"):
            validate_source("0004_kafka.py", "operations = []")


if __name__ == "__main__":
    unittest.main()
