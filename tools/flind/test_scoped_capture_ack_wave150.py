#!/usr/bin/env python3
"""Wave150 regression: capture-disabled cannot set BudgetSteer durable ACK."""
from __future__ import annotations

import ast
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime
import os
from pathlib import Path
from typing import Any
import unittest

ROOT = Path(os.environ.get("FLIND_SOURCE_ROOT", Path(__file__).resolve().parents[2]))


def actual_scoped_capture(client):
    source = ast.parse((ROOT / "posthog/ph_client.py").read_text())
    clazz = next(node for node in source.body
                 if isinstance(node, ast.ClassDef) and node.name == "ScopedCapture")
    fn = next(node for node in source.body
              if isinstance(node, ast.FunctionDef) and node.name == "ph_scoped_capture")
    scope = {
        "contextmanager": contextmanager, "get_client": lambda *a, **kw: client,
        "is_cloud": lambda: True, "Any": Any, "Iterator": Iterator,
    }
    exec(compile(ast.Module(body=[clazz, fn], type_ignores=[]),
                 "<real Flind scoped capture>", "exec"), scope)
    return scope["ph_scoped_capture"]


class FakeRedis:
    def __init__(self):
        self.stamps = []
    def exists(self, key):
        return False
    def set(self, *args, **kwargs):
        self.stamps.append((args, kwargs))


def actual_budget_steer_capture(redis, scoped):
    tree = ast.parse((ROOT / "products/tasks/backend/logic/stream/budget_steer.py").read_text())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BudgetSteerCapture")
    func = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == "capture")
    func.decorator_list = []
    scope = {
        "get_tasks_stream_redis_sync": lambda: redis,
        "ph_scoped_capture": scoped,
        "datetime": datetime,
        "BUDGET_STEER_RETENTION_SECONDS": 3600,
        "BudgetSteerProperties": dict,
    }
    exec(compile(ast.Module(body=[func], type_ignores=[]),
                 "<real BudgetSteerCapture.capture>", "exec"), scope)
    return scope["capture"]


class FlindCaptureACKWave150(unittest.TestCase):
    def test_strict_scoped_capture_refuses_missing_client(self):
        scoped = actual_scoped_capture(None)
        with self.assertRaisesRegex(RuntimeError, "Flind analytics capture is not configured"):
            with scoped(raise_on_error=True):
                self.fail("strict unconfigured context unexpectedly yielded")

    def test_budget_steer_does_not_checkpoint_when_no_client(self):
        redis = FakeRedis()
        capture = actual_budget_steer_capture(redis, actual_scoped_capture(None))
        with self.assertRaisesRegex(RuntimeError, "Flind analytics capture is not configured"):
            capture(7, "test-event", "2026-01-01T00:00:00", {"test": "local"})
        self.assertEqual(redis.stamps, [])

    def test_default_non_strict_scope_remains_safe_noop(self):
        scoped = actual_scoped_capture(None)
        with scoped() as capture:
            capture(distinct_id="team_7", event="no-op")
        # No SDK, no exception, no outbound traffic.

    def test_configured_client_does_not_regress_capture_ack(self):
        class FakeClient:
            def __init__(self):
                self.events = []
                self.closed = False
            def capture(self, *args, **kwargs):
                self.events.append((args, kwargs))
                return "fake-accepted"
            def shutdown(self):
                self.closed = True
        client = FakeClient()
        redis = FakeRedis()
        capture = actual_budget_steer_capture(redis, actual_scoped_capture(client))
        capture(7, "owned-test-event", "2026-01-01T00:00:00", {"test": "owned"})
        self.assertEqual(len(client.events), 1)
        self.assertTrue(client.closed)
        self.assertEqual(len(redis.stamps), 1)
        self.assertIn("owned-test-event:captured", redis.stamps[0][0][0])


if __name__ == "__main__":
    unittest.main()
