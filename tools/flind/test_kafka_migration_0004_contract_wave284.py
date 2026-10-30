"""Source-only, fail-closed contract for the original 0004 Kafka migration.

No Django imports, network, Kafka, ClickHouse, or migration execution. This
protects the historical six-step order while live owner-only qualification is
pending. It is NOT a database or product end-to-end test.
"""

import ast
import unittest
from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[2] / "posthog/clickhouse/migrations/0004_kafka.py"
EXPECTED = (
    "run_sql_with_exceptions(KAFKA_PERSONS_TABLE_SQL())",
    "run_sql_with_exceptions(KAFKA_PERSONS_DISTINCT_ID_TABLE_SQL())",
    "run_sql_with_exceptions(PERSONS_TABLE_MV_SQL(target_table=PERSONS_TABLE))",
    "run_sql_with_exceptions(PERSONS_DISTINCT_ID_TABLE_MV_SQL())",
    "run_sql_with_exceptions(WRITABLE_EVENTS_TABLE_SQL())",
    "run_sql_with_exceptions(DISTRIBUTED_EVENTS_TABLE_SQL())",
)
EXPECTED_IMPORTS = {
    "posthog.clickhouse.client.migration_tools": {"run_sql_with_exceptions"},
    "posthog.models.event.sql": {"DISTRIBUTED_EVENTS_TABLE_SQL", "WRITABLE_EVENTS_TABLE_SQL"},
    "posthog.models.person.sql": {
        "KAFKA_PERSONS_DISTINCT_ID_TABLE_SQL", "KAFKA_PERSONS_TABLE_SQL",
        "PERSONS_DISTINCT_ID_TABLE_MV_SQL", "PERSONS_TABLE", "PERSONS_TABLE_MV_SQL",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("FLIND_W284_SOURCE_CONTRACT: " + message)


def validate_source(source: str) -> int:
    tree = ast.parse(source, filename="0004_kafka.py")
    require(len(tree.body) == 4, "expected exactly three imports and one operations assignment")
    imports = {}
    for node in tree.body[:3]:
        require(isinstance(node, ast.ImportFrom) and node.level == 0, "unexpected import or executable statement")
        require(node.module not in imports, "duplicate import module")
        require(all(alias.asname is None for alias in node.names), "aliased import")
        imports[node.module] = {alias.name for alias in node.names}
    require(imports == EXPECTED_IMPORTS, "migration import contract changed")
    assignment = tree.body[3]
    require(isinstance(assignment, ast.Assign), "operations must be assigned directly")
    require(len(assignment.targets) == 1 and isinstance(assignment.targets[0], ast.Name)
            and assignment.targets[0].id == "operations", "unexpected operations target")
    require(isinstance(assignment.value, ast.List), "operations must be a literal ordered list")
    actual = assignment.value.elts
    require(len(actual) == len(EXPECTED), "six historical migration operations required")
    for index, (node, expression) in enumerate(zip(actual, EXPECTED)):
        expected = ast.parse(expression, mode="eval").body
        require(ast.dump(node, include_attributes=False) == ast.dump(expected, include_attributes=False),
                f"operation {index + 1} differs from source-locked order/arguments")
    return len(actual)


class OriginalKafkaMigrationSourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MIGRATION.read_text(encoding="utf-8")

    def test_exact_original_migration_contract(self):
        self.assertEqual(validate_source(self.source), 6)

    def test_negative_control_removed_operation(self):
        changed = self.source.replace("    run_sql_with_exceptions(WRITABLE_EVENTS_TABLE_SQL()),\n", "", 1)
        self.assertNotEqual(changed, self.source)
        with self.assertRaisesRegex(RuntimeError, "six historical"):
            validate_source(changed)

    def test_negative_control_reordered_operations(self):
        before = "    run_sql_with_exceptions(KAFKA_PERSONS_TABLE_SQL()),\n    run_sql_with_exceptions(KAFKA_PERSONS_DISTINCT_ID_TABLE_SQL()),"
        after = "    run_sql_with_exceptions(KAFKA_PERSONS_DISTINCT_ID_TABLE_SQL()),\n    run_sql_with_exceptions(KAFKA_PERSONS_TABLE_SQL()),"
        changed = self.source.replace(before, after, 1)
        self.assertNotEqual(changed, self.source)
        with self.assertRaisesRegex(RuntimeError, "operation 1"):
            validate_source(changed)

    def test_negative_control_unwrapped_operation(self):
        changed = self.source.replace("run_sql_with_exceptions(KAFKA_PERSONS_TABLE_SQL())", "KAFKA_PERSONS_TABLE_SQL()", 1)
        self.assertNotEqual(changed, self.source)
        with self.assertRaisesRegex(RuntimeError, "operation 1"):
            validate_source(changed)

    def test_negative_control_unexpected_destructive_sql(self):
        changed = self.source.replace("operations = [", "operations = [\n    run_sql_with_exceptions('DROP TABLE kafka_persons'),", 1)
        self.assertNotEqual(changed, self.source)
        with self.assertRaisesRegex(RuntimeError, "six historical"):
            validate_source(changed)

    def test_negative_control_unexpected_top_level_execution(self):
        changed = self.source + "\nprint('unexpected side effect')\n"
        with self.assertRaisesRegex(RuntimeError, "three imports"):
            validate_source(changed)

    def test_negative_control_modified_materialized_view_target(self):
        changed = self.source.replace("target_table=PERSONS_TABLE", "target_table='other'", 1)
        self.assertNotEqual(changed, self.source)
        with self.assertRaisesRegex(RuntimeError, "operation 3"):
            validate_source(changed)

    def test_negative_control_import_alias(self):
        changed = self.source.replace("import run_sql_with_exceptions", "import run_sql_with_exceptions as other", 1)
        self.assertNotEqual(changed, self.source)
        with self.assertRaisesRegex(RuntimeError, "aliased import"):
            validate_source(changed)


if __name__ == "__main__":
    unittest.main()
