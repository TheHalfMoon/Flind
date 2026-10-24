"""Verify both temporary services overlap and release qualification stays false."""
from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

from tools.flind import qualify_ephemeral_stack as stack


class EphemeralStackWave50Tests(unittest.TestCase):
    @patch.object(stack, "isolated_clickhouse")
    @patch.object(stack, "isolated_redis")
    def test_nested_clickhouse_runs_while_redis_port_is_ready(self, redis, clickhouse):
        redis.side_effect = lambda on_ready: {
            "isolated_redis_passed": True,
            "nested_clickhouse": on_ready(16379),
        }
        clickhouse.return_value = {
            "isolated_clickhouse_passed": True,
            "http_query_roundtrip": {"rows": 3, "sum": 60},
            "backend_prerequisites": {
                "prerequisites_ready": True,
                "release_qualified": False,
                "blocked_by": [],
            },
        }
        result = stack.qualify_stack()
        self.assertTrue(result["stack_prerequisites_passed"])
        self.assertFalse(result["release_qualified"])
        self.assertEqual(result["clickhouse_http_sql_roundtrip"], {"rows": 3, "sum": 60})
        clickhouse.assert_called_once_with(redis_port=16379)

    @patch.object(stack, "isolated_redis")
    def test_partial_success_never_claims_all_prerequisites(self, redis):
        redis.return_value = {
            "isolated_redis_passed": True,
            "nested_clickhouse": {
                "isolated_clickhouse_passed": True,
                "backend_prerequisites": {
                    "prerequisites_ready": False,
                    "blocked_by": ["python"],
                    "release_qualified": False,
                },
            },
        }
        self.assertFalse(stack.qualify_stack()["stack_prerequisites_passed"])

    @patch.object(stack, "isolated_redis")
    def test_missing_service_does_not_qualify(self, redis):
        redis.return_value = {"isolated_redis_passed": False}
        result = stack.qualify_stack()
        self.assertFalse(result["stack_prerequisites_passed"])
        self.assertFalse(result["release_qualified"])

    @patch.object(stack, "qualify_stack", return_value={
        "stack_prerequisites_passed": False, "release_qualified": False,
    })
    def test_cli_exits_nonzero_on_blocker(self, _qualify):
        with redirect_stdout(StringIO()) as output:
            code = stack.main(["--json"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())["release_qualified"])


if __name__ == "__main__":
    unittest.main()
