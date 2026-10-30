"""Wave283: run 13 original HogQL namespaced lazy-table tests inside real Django.

Owner-only manual test with original test class AST and real HogQL compiler.
No test.BaseTest import, database access, outgoing socket, or production effects.
The source overlay is explicitly pinned to the tested original Flind PR blob.
This is NOT the entire HogQL pytest suite or an end-to-end qualification.
"""
from __future__ import annotations

import ast
import importlib.metadata
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch


SOURCE_BLOBS = {
    "posthog/hogql/transforms/lazy_tables.py": "a6b57b31c971900aceaf277c20628b912f0bbe6e",
    "posthog/hogql/transforms/test/test_lazy_tables.py": "1dd2e0c15db5931d904fa71129dfcfd195bd3d06",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("W283_FAIL_CLOSED: " + message)


def run() -> int:
    raw_root = os.environ.get("FLIND_W283_OWNER_ROOT", "")
    require(bool(raw_root), "set FLIND_W283_OWNER_ROOT")
    root = Path(raw_root).resolve()
    require(root.parent == Path("/private/tmp"), "owner-only macOS scratch root required")
    require(
        (root / ".flind-owner-only").read_text() == "FLIND_WAVE283_OWNER_ONLY_NATIVE_HOGQL_SMOKE\n",
        "scratch owner marker missing",
    )
    source = root / "source"
    require(source.is_dir() and (source / ".git").exists(), "original source checkout missing")
    expected_base = "6e5da8f24fb04312ea1dd7778811ca1b21339fd9"
    base = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    require(base == expected_base, "original full source base drift")
    for relative, expected in SOURCE_BLOBS.items():
        path = source / relative
        require(path.is_file(), "source missing: " + relative)
        blob = subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()
        require(blob == expected, "authentic first-party source hash mismatch: " + relative)
    require(sys.version_info[:3] == (3, 14, 7), "Python 3.14.7 required")
    for package, version in [("django", "5.2.18"), ("parameterized", "0.9.0")]:
        require(importlib.metadata.version(package) == version, package + " version drift")
    signal.alarm(85)
    os.environ.clear()
    os.environ.update(
        {
            "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
            "HOME": str(root),
            "TMPDIR": str(root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DJANGO_SETTINGS_MODULE": "posthog.settings",
            "SECRET_KEY": "flind-wave283-hogql-synthetic",
            "DATABASE_URL": "postgresql://invalid@127.0.0.1:1/flind_w283",
            "REDIS_URL": "redis://127.0.0.1:1/0",
            "CLICKHOUSE_HOST": "127.0.0.1",
            "CLICKHOUSE_PORT": "1",
            "CLICKHOUSE_HTTP_URL": "http://127.0.0.1:1",
            "KAFKA_HOSTS": "127.0.0.1:1",
            "SENTRY_DSN": "",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    os.chdir(root)
    sys.path.insert(0, str(source))

    def reject_network(*args, **kwargs):
        raise RuntimeError("W283_ALL_NETWORK_CONNECTIONS_DENIED")

    socket.socket.connect = reject_network
    socket.socket.connect_ex = reject_network
    socket.socket.sendto = reject_network
    socket.create_connection = reject_network

    import django

    django.setup()
    print("W283_NATIVE_DJANGO_BOOTSTRAP_PASS", flush=True)

    from django.test import SimpleTestCase
    from parameterized import parameterized
    from posthog.hogql.context import HogQLContext
    from posthog.hogql.database.database import Database
    from posthog.hogql.parser import parse_select
    from posthog.hogql.printer import prepare_and_print_ast
    from posthog.hogql.property_metadata import PropertyMetadata
    from posthog.models import Organization, Team

    test_file = source / "posthog/hogql/transforms/test/test_lazy_tables.py"
    tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TestNamespacedLazyTables"
    ]
    require(len(classes) == 1, "original first-party test class count drift")
    module = ast.Module(body=[classes[0]], type_ignores=[])
    scope = {
        "__name__": "flind_w283_authentic_hogql_tests",
        "SimpleTestCase": SimpleTestCase,
        "parameterized": parameterized,
        "HogQLContext": HogQLContext,
        "Team": Team,
        "Organization": Organization,
        "Database": Database,
        "parse_select": parse_select,
        "prepare_and_print_ast": prepare_and_print_ast,
        "PropertyMetadata": PropertyMetadata,
        "patch": patch,
    }
    exec(compile(ast.fix_missing_locations(module), str(test_file), "exec"), scope)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        scope["TestNamespacedLazyTables"]
    )
    require(suite.countTestCases() == 13, "original first-party test count drift")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    require(
        result.wasSuccessful() and result.testsRun == 13,
        "real Django/HogQL original first-party tests not green",
    )
    print("W283_REAL_DJANGO_ORIGINAL_HOGQL_13_OF_13_PASS", flush=True)
    print("W283_NO_DATABASE_OR_NETWORK_OPERATIONS_PERMITTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
