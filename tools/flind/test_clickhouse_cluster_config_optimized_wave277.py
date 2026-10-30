"""Isolated original get_cluster() configuration guard regression; no network/database."""
import ast
import os
import unittest
from copy import copy
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(os.environ["FLIND_CLUSTER_SOURCE"]) if "FLIND_CLUSTER_SOURCE" in os.environ else Path(__file__).resolve().parents[2] / "posthog/clickhouse/cluster.py"

def make_get_cluster(config):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_cluster"]
    if len(funcs) != 1:
        raise RuntimeError("Original get_cluster source missing or ambiguous")
    calls = []
    settings = SimpleNamespace(CLICKHOUSE_HOST="127.0.0.1", CLICKHOUSE_USER="synthetic")
    def default_client(**kwargs):
        calls.append(("client", kwargs))
        return "synthetic-client"
    def fake_cluster(client, **kwargs):
        calls.append(("cluster", kwargs))
        return kwargs
    ns = {
        "settings": settings, "ClickHouseUser": SimpleNamespace(DEFAULT="synthetic"),
        "CLICKHOUSE_PER_TEAM_SETTINGS": config, "copy": copy,
        "ConnectionInfo": lambda host, shard: (host, shard),
        "get_clickhouse_creds": lambda user: SimpleNamespace(user="synthetic", password="fake"),
        "is_file_backed_user": lambda creds, user: False,
        "default_client": default_client, "ClickhouseCluster": fake_cluster,
    }
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), funcs[0]],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), ns)
    return ns["get_cluster"], calls

class ClusterConfigGuardTests(unittest.TestCase):
    def test_unknown_host_field_fails_closed(self):
        fn, calls = make_get_cluster({"team101": {"host": "127.0.0.1", "unexpected": "synthetic"}})
        with self.assertRaisesRegex(AssertionError, "unexpected values"):
            fn()
        self.assertEqual(calls, [])

    def test_second_host_unknown_field_fails_closed(self):
        fn, calls = make_get_cluster({
            "team101": {"host": "127.0.0.1"},
            "team202": {"host": "127.0.0.2", "unknown": True},
        })
        with self.assertRaisesRegex(AssertionError, "unexpected values"):
            fn()
        self.assertEqual(calls, [])

    def test_valid_host_configuration(self):
        fn, calls = make_get_cluster({"team101": {"host": "127.0.0.1"}})
        result = fn()
        self.assertEqual(result["extra_hosts"], [("127.0.0.1", None)])
        self.assertEqual([name for name, _ in calls], ["client", "cluster"])

    def test_original_config_not_mutated(self):
        config = {"team101": {"host": "127.0.0.1"}}
        fn, _ = make_get_cluster(config)
        fn()
        self.assertEqual(config, {"team101": {"host": "127.0.0.1"}})

if __name__ == "__main__":
    unittest.main()
