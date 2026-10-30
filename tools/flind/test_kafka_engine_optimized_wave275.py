"""Pure source-backed Kafka engine argument checks, including Python -O.

This intentionally tests only the original function body and constants; it does
not bootstrap Django or establish a live Kafka/ClickHouse connection.
"""

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


def load_source_function():
    path = Path(__file__).resolve().parents[2] / "posthog/clickhouse/kafka_engine.py"
    source = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    constants = {"KAFKA_ENGINE", "KAFKA_NAMED_COLLECTION_ENGINE"}
    nodes = [
        node
        for node in source.body
        if (isinstance(node, ast.FunctionDef) and node.name == "kafka_engine")
        or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets))
    ]
    if len(nodes) != 3:
        raise RuntimeError("Original Kafka engine function/constants not uniquely located")
    namespace = {"settings": SimpleNamespace(CLICKHOUSE_KAFKA_NAMED_COLLECTION="flind_wave275_owner_only")}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["kafka_engine"]


class KafkaEngineOptimizedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = staticmethod(load_source_function())

    def test_named_collection_rejects_explicit_host(self):
        with self.assertRaisesRegex(AssertionError, "Can't set kafka_host when using named collection"):
            self.engine("synthetic", kafka_host="127.0.0.1:9092")

    def test_named_collection_default(self):
        self.assertIn("flind_wave275_owner_only", self.engine("synthetic"))

    def test_named_collection_override(self):
        self.assertIn("flind_wave275_override", self.engine("synthetic", named_collection="flind_wave275_override"))

    def test_explicit_broker_mode(self):
        self.assertIn("127.0.0.1:9092", self.engine("synthetic", kafka_host="127.0.0.1:9092", use_named_collection=False))

    def test_explicit_broker_mode_requires_host(self):
        with self.assertRaisesRegex(ValueError, "kafka_host is required"):
            self.engine("synthetic", use_named_collection=False)


if __name__ == "__main__":
    unittest.main()
