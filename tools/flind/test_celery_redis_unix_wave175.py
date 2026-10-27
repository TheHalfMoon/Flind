"""Wave175: validate first-party Kombu Redis Unix URL without external services."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from kombu import Connection


class CeleryRedisUnixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[2] / "posthog/settings/celery.py"
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        function = next(
            (node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == "flind_celery_redis_url"),
            None,
        )
        if function is None:
            raise AssertionError("Flind Celery Redis URL helper missing")
        local = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), local)
        cls.normalize = staticmethod(local["flind_celery_redis_url"])
        cls.source = tree

    def test_unix_django_redis_url_maps_to_kombu(self):
        self.assertEqual(
            self.normalize("unix:///private/tmp/flind/redis.sock?db=0"),
            "redis+socket:///private/tmp/flind/redis.sock?db=0",
        )

    def test_queries_and_paths_remain_unchanged(self):
        self.assertEqual(
            self.normalize("unix:///private/tmp/flind-with-space/redis.sock?db=1&socket_timeout=3"),
            "redis+socket:///private/tmp/flind-with-space/redis.sock?db=1&socket_timeout=3",
        )

    def test_tcp_and_tls_redis_urls_remain_intact(self):
        for original in ("redis://localhost:6379/0", "rediss://flind.example:6380/1",
                         "redis+socket:///private/tmp/flind.sock?db=0"):
            self.assertEqual(self.normalize(original), original)

    def test_unix_host_form_is_not_silently_rewritten(self):
        self.assertEqual(self.normalize("unix://server/not-local.sock"), "unix://server/not-local.sock")

    def test_broker_and_result_backend_both_use_same_normalizer(self):
        assignments = {}
        for node in self.source.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in (
                        "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
                    ):
                        assignments[target.id] = node.value
        self.assertEqual(set(assignments), {"CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"})
        for expression in assignments.values():
            self.assertIsInstance(expression, ast.Call)
            self.assertIsInstance(expression.func, ast.Name)
            self.assertEqual(expression.func.id, "flind_celery_redis_url")

    def test_real_kombu_loader_recognizes_translated_redis_transport(self):
        broker = self.normalize("unix:///private/tmp/flind-test.sock?db=0")
        connection = Connection(broker)
        self.assertEqual(connection.transport_cls, "redis")
        self.assertIn("socket://", connection.hostname)

    def test_untranslated_django_unix_url_is_not_a_kombu_transport(self):
        with self.assertRaises(KeyError):
            Connection("unix:///private/tmp/flind-test.sock?db=0").transport

    def test_nonnative_unknown_scheme_kept_fail_closed(self):
        self.assertEqual(self.normalize("something://no-service"), "something://no-service")


if __name__ == "__main__":
    unittest.main()
