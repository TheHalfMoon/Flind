"""Wave269: source-attested native Django migration import and original product pytest.

Manual owner-only qualification. No SQL migrations are run. Refuses all socket
connections, uses synthetic settings, and requires a marked disposable checkout.
Do not interpret this as live ClickHouse, multi-node or release qualification.
"""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys


EXPECTED = {
    "posthog/clickhouse/client/connection.py": "586900ac49ea84eb1315dd7169a824b15cae1b0c",
    "posthog/clickhouse/client/migration_tools.py": "17a082e56f6c2825279e8337d1572be921b0aeac",
    "posthog/management/commands/migrate_clickhouse.py": "a3292548f7b3564ea265c232c3f9c43df933c410",
    "posthog/management/commands/test/test_migrate_clickhouse.py": "1100c2fe67cc82c72deb0c68b7afd87c7e080560",
    "posthog/models/channel_type/channel_definitions.json": "cf1dde05b31220be591aecc2c197fda5ca4659f1",
    "posthog/models/exchange_rate/historical.csv": "048be5f3d1b30dd89bbce3ca32d833e148a0fdd1",
}
MIGRATION_TREE = "23ea2f226e6be4f2caca554b6ef7cd769d61baa0"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("W269_FAIL_CLOSED: " + message)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def main() -> int:
    root_value = os.environ.get("FLIND_W269_SOURCE_ROOT")
    require(bool(root_value), "FLIND_W269_SOURCE_ROOT is required")
    source = Path(root_value).resolve()
    owner_root = source.parent
    require(source.name == "source" and source.is_dir(), "disposable source/ directory required")
    require(owner_root.is_relative_to(Path("/private/tmp")), "owner-only macOS scratch required")
    require((owner_root / ".flind-wave269-owner").is_file(), "owner-only marker missing")
    require(
        git(source, "rev-parse", "HEAD:posthog/clickhouse/migrations") == MIGRATION_TREE,
        "migration source tree drift",
    )
    for relative, sha in EXPECTED.items():
        target = source / relative
        require(target.is_file(), "required original tracked asset missing: " + relative)
        require(git(source, "hash-object", str(target)) == sha, "source Git blob mismatch: " + relative)

    versions = {
        "django": "5.2.18",
        "pytest": "9.1.1",
        "infi-clickhouse-orm": "2.1.0.post20",
        "requests": "2.33.0",
        "responses": "0.23.1",
    }
    for name, version in versions.items():
        require(importlib.metadata.version(name) == version, "dependency drift: " + name)
    direct = importlib.metadata.distribution("infi-clickhouse-orm").read_text("direct_url.json")
    require(
        bool(direct)
        and json.loads(direct).get("vcs_info", {}).get("commit_id")
        == "4e3996becf66bf5c26580aff12a80425d9d56fe5",
        "pinned original infi Git revision drift",
    )
    require(sys.version_info[:3] == (3, 14, 7), "Python 3.14.7 required")
    signal.alarm(90)

    os.environ.clear()
    os.environ.update(
        {
            "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
            "HOME": str(owner_root),
            "TMPDIR": str(owner_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DJANGO_SETTINGS_MODULE": "posthog.settings",
            "SECRET_KEY": "flind-wave269-synthetic-only",
            "DATABASE_URL": "postgresql://flind_invalid@127.0.0.1:1/flind_wave269_synthetic",
            "REDIS_URL": "redis://127.0.0.1:1/0",
            "CLICKHOUSE_HOST": "127.0.0.1",
            "CLICKHOUSE_PORT": "1",
            "CLICKHOUSE_HTTP_URL": "http://127.0.0.1:1",
            "KAFKA_HOSTS": "127.0.0.1:1",
            "SENTRY_DSN": "",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    os.chdir(owner_root)
    sys.path.insert(0, str(source))

    def reject_network(*args: object, **kwargs: object) -> None:
        raise RuntimeError("W269_ALL_NETWORK_CONNECTIONS_REFUSED")

    socket.socket.connect = reject_network
    socket.socket.connect_ex = reject_network
    socket.create_connection = reject_network
    socket.socket.sendto = reject_network

    import django

    django.setup()
    print("W269_NATIVE_DJANGO_SETUP_PASS", flush=True)

    from infi.clickhouse_orm.utils import import_submodules
    from posthog.management.commands.migrate_clickhouse import Command

    package = "posthog.clickhouse.migrations"
    modules = import_submodules(package)
    expected_names = {
        path.stem
        for path in (source / "posthog/clickhouse/migrations").glob("*.py")
        if path.name[:4].isdigit() and path.name[4:5] == "_"
    }
    require(len(modules) == 346, "native migration import count is not 346")
    require(set(modules) == expected_names, "native migration module names mismatch")
    require(all(hasattr(module, "operations") for module in modules.values()), "missing original operations")
    require("0067_event_kafka_debug_table copy" in modules, "historical migration lost")
    print("W269_NATIVE_346_MIGRATION_IMPORT_PASS", flush=True)

    command = Command()
    command.get_applied_migrations = lambda database: set()
    for upto in (0, 4, 5, 29, 50, 55, 83, 337, 359, 99_999):
        selected = [name for name, _ in command.get_migrations(object(), upto)]
        expected_names_bounded = sorted(
            name for name in expected_names if int(name[:4]) <= upto
        )
        require(selected == expected_names_bounded, "original upto boundary failed: " + str(upto))
    applied = set(sorted(expected_names)[:35])
    command.get_applied_migrations = lambda database: set(applied)
    actual = [name for name, _ in command.get_migrations(object(), 55)]
    expected_applied = sorted(
        name for name in expected_names if int(name[:4]) <= 55 and name not in applied
    )
    require(actual == expected_applied, "already-applied original selection mismatch")
    print("W269_ORIGINAL_MIGRATION_SELECTION_PASS", flush=True)

    from qualify_native_plan_cases_wave269 import run_all
    run_all()

    import pytest

    product_test = source / "posthog/management/commands/test/test_migrate_clickhouse.py"
    exit_code = int(
        pytest.main(
            [
                "--noconftest", "-q", "-p", "no:cacheprovider",
                "-o", "addopts=", "--disable-warnings", str(product_test),
            ]
        )
    )
    require(exit_code == 0, "first-party full-Django pytest failed")
    print("W269_FULL_DJANGO_FIRST_PARTY_PYTEST_PASS", flush=True)
    print("W269_FULL_DJANGO_MOCK_PLAN_CHECK_QUALIFICATION_DONE; NO SQL MIGRATIONS APPLIED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
