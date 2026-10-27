#!/usr/bin/env python3
"""Qualify a read-only Flind migration plan and a reversible first-party smoke migration.

Use only a marked, dedicated temporary PostgreSQL cluster with Unix sockets.
Never call this on a shared DB; never infer full migration/release qualification.
"""
from __future__ import annotations
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time

PG_MARKER = ".flind-isolated-pg-v1"
PG_MARKER_TEXT = "FLIND_ISOLATED_PG_V1\n"
SOURCE_MARKER = ".flind-migration-scratch-v1"
SOURCE_MARKER_TEXT = "FLIND_MIGRATION_SCRATCH_V1\n"
SYNTHETIC_DB_RE = re.compile(r"flind_wave[0-9]+_synthetic(?:_[a-z0-9]+)?\Z")
# Only this isolated, dependency-free first-party CreateModel was inspected.
SMOKE_APP = "ai_training"
SMOKE_MIGRATION = "0001_initial"


def safe_locations(source: Path, data_dir: Path, socket_dir: Path,
                   port: int, database: str) -> bool:
    """Fail closed before any PostgreSQL or background app connection."""
    try:
        if not 1025 <= port <= 65535 or not SYNTHETIC_DB_RE.fullmatch(database):
            return False
        for root in (source, data_dir, socket_dir):
            if root.is_symlink() or not root.is_dir() or not root.is_absolute():
                return False
        # Never admit shared /opt/homebrew PostgreSQL or a production Unix socket.
        sandbox = Path("/private/tmp").resolve()
        for root in (source, data_dir, socket_dir):
            target = root.resolve()
            if sandbox not in target.parents:
                return False
        if source.resolve() in data_dir.resolve().parents or data_dir.resolve() in source.resolve().parents:
            return False
        if (source / SOURCE_MARKER).read_text() != SOURCE_MARKER_TEXT:
            return False
        if (data_dir / PG_MARKER).read_text() != PG_MARKER_TEXT:
            return False
        if not (data_dir / "PG_VERSION").is_file():
            return False
        if not (socket_dir / f".s.PGSQL.{port}").exists():
            return False
        return (source / ".git").exists() and (source / "pyproject.toml").is_file()
    except (OSError, UnicodeError, ValueError):
        return False


def expected_migration(migration, plan) -> bool:
    if migration is None or migration.dependencies or len(migration.operations) != 1:
        return False
    operation = migration.operations[0]
    if type(operation).__name__ != "CreateModel":
        return False
    if any(getattr(field, "remote_field", None) for _, field in operation.fields):
        return False
    return len(plan) == 1 and plan[0][0].app_label == SMOKE_APP and plan[0][0].name == SMOKE_MIGRATION and not plan[0][1]


def execute(root: Path, git_ref: str, data_dir: Path, socket_dir: Path,
            port: int, dbname: str, *, apply_rollback: bool = False) -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "isolated-postgres-flind-migration-plan",
        "django_registry_qualified": False,
        "migration_graph_qualified": False,
        "postgres_readonly_connection_qualified": False,
        "migration_plan_qualified": False,
        "one_first_party_apply_qualified": False,
        "one_first_party_rollback_qualified": False,
        "full_migrations_qualified": False,
        "full_rollback_qualified": False,
        "release_qualified": False,
        "apply_rollback_requested": apply_rollback,
    }
    start = time.monotonic()
    try:
        if not safe_locations(root, data_dir, socket_dir, port, dbname):
            raise ValueError("unsafe_database_or_source_target")
        signal.alarm(150)
        os.environ.update({
            "DJANGO_SETTINGS_MODULE": "posthog.settings",
            "SECRET_KEY": "flind_synthetic_isolated_pg_testing_only",
            "DATABASE_URL": f"postgres://{getpass.getuser()}@/{dbname}?host={socket_dir}&port={port}",
            "POSTHOG_DB_NAME": dbname,
            "PGHOST": str(socket_dir),
            "PGPORT": str(port),
            "PGDATABASE": dbname,
            "REDIS_URL": "redis://127.0.0.1:65434/0",
            "CLICKHOUSE_HOST": "127.0.0.1",
            "CLICKHOUSE_PORT": "65435",
            "KAFKA_HOSTS": "127.0.0.1:65437",
            "PYTHONDONTWRITEBYTECODE": "1",
            "DISABLE_MMDB": "true",
        })
        # Support direct script invocation from anywhere, not just module mode.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from tools.flind.qualify_sparse_django_registry_wave147 import (
            index_tracked_python, graph_source_ready, git_offline_env,
            GitBlobBatchReader, GitTrackedPythonFinder,
        )
        git = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", git_ref + "^{commit}"],
            capture_output=True, check=False, timeout=20, env=git_offline_env(),
        )
        sha = git.stdout.decode("ascii").strip()
        if git.returncode or len(sha) != 40 or not re.fullmatch(r"[a-f0-9]+", sha):
            raise ValueError("unverified_source_commit")
        report["source_commit"] = sha
        tracked = index_tracked_python(root, git_ref)
        ready, count = graph_source_ready(root, tracked)
        if not ready:
            raise ValueError("migration_source_tree_incomplete")
        report["migration_files_staged"] = count
        sock_path = str(socket_dir / f".s.PGSQL.{port}")
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex

        def restricted_connect(sock, address):
            if sock.family == socket.AF_UNIX and address == sock_path:
                return original_connect(sock, address)
            raise OSError("Flind isolated PostgreSQL-only socket policy")

        def restricted_connect_ex(sock, address):
            if sock.family == socket.AF_UNIX and address == sock_path:
                return original_connect_ex(sock, address)
            raise OSError("Flind isolated PostgreSQL-only socket policy")

        socket.socket.connect = restricted_connect
        socket.socket.connect_ex = restricted_connect_ex

        def deny_tcp(*args, **kwargs):
            raise OSError("Flind isolated test blocks TCP")
        socket.create_connection = deny_tcp
        sys.path.insert(0, str(root))
        with GitBlobBatchReader(root, git_ref) as reader:
            finder = GitTrackedPythonFinder(
                root, git_ref, tracked, limit=2600, deadline=140, batch_reader=reader,
            )
            sys.meta_path.append(finder)
            import django
            django.setup()
            from django.apps import apps
            report["django_registry_qualified"] = True
            report["app_count"] = len(apps.get_app_configs())
            from django.db import connections
            from django.db.migrations.executor import MigrationExecutor
            connection = connections["default"]
            settings = connection.settings_dict
            options = settings.get("OPTIONS", {})
            if (settings["NAME"] != dbname or options.get("host") != str(socket_dir)
                    or int(options.get("port", 0)) != port):
                raise ValueError("unexpected_django_postgres_config")
            with connection.cursor() as cursor:
                cursor.execute("SET default_transaction_read_only = on")
                cursor.execute("SELECT current_database(), inet_server_addr() IS NULL")
                actual_db, unix_socket = cursor.fetchone()
                cursor.execute("SHOW data_directory")
                actual_data_dir = Path(cursor.fetchone()[0]).resolve()
                cursor.execute("SHOW default_transaction_read_only")
                read_only = cursor.fetchone()[0] == "on"
            if (actual_db != dbname or not unix_socket or not read_only
                    or actual_data_dir != data_dir.resolve()):
                raise ValueError("postgres_isolation_not_verified")
            report["postgres_readonly_connection_qualified"] = True
            executor = MigrationExecutor(connection)
            report["migration_graph_nodes"] = len(executor.loader.graph.nodes)
            report["disk_migrations"] = len(executor.loader.disk_migrations)
            report["migration_graph_qualified"] = bool(report["migration_graph_nodes"] and report["disk_migrations"])
            leaf_targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(leaf_targets)
            report["migration_plan_qualified"] = report["migration_graph_qualified"]
            report["planned_migrations"] = len(plan)
            report["leaf_targets"] = len(leaf_targets)

            if apply_rollback:
                target = (SMOKE_APP, SMOKE_MIGRATION)
                candidate = executor.loader.disk_migrations.get(target)
                plan_one = executor.migration_plan([target])
                if not expected_migration(candidate, plan_one):
                    raise ValueError("unsafe_first_party_migration")
                with connection.cursor() as cursor:
                    cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'")
                    initial_tables = {v[0] for v in cursor.fetchall()}
                    if initial_tables - {"django_migrations"}:
                        raise ValueError("isolated_db_has_user_tables")
                    if "django_migrations" in initial_tables:
                        cursor.execute("SELECT count(*) FROM django_migrations")
                        if cursor.fetchone()[0] != 0:
                            raise ValueError("isolated_db_has_applied_migrations")
                    cursor.execute("SET default_transaction_read_only = off")
                try:
                    executor = MigrationExecutor(connection)
                    executor.migrate([target])
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT count(*) FROM django_migrations WHERE app=%s AND name=%s",
                            target,
                        )
                        recorded = cursor.fetchone()[0]
                    if recorded != 1:
                        raise RuntimeError("first_party_migration_not_recorded")
                    report["one_first_party_apply_qualified"] = True
                finally:
                    # Always attempt to undo only our one scoped migration.
                    rollback = MigrationExecutor(connection)
                    rollback.migrate([(SMOKE_APP, None)])
                with connection.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM django_migrations WHERE app=%s", (SMOKE_APP,))
                    rows = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT tablename FROM pg_catalog.pg_tables "
                        "WHERE schemaname='public' AND tablename <> 'django_migrations'"
                    )
                    tables = [row[0] for row in cursor.fetchall()]
                    cursor.execute("SET default_transaction_read_only = on")
                report["remaining_app_migration_records"] = rows
                report["remaining_user_tables"] = len(tables)
                report["one_first_party_rollback_qualified"] = rows == 0 and not tables
                if not report["one_first_party_rollback_qualified"]:
                    raise RuntimeError("first_party_rollback_incomplete")
            connection.close()
    except Exception as exc:
        report["blocker"] = type(exc).__name__
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - start, 1)
        signal.alarm(0)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--ref", default="HEAD")
    p.add_argument("--pg-data", type=Path, required=True)
    p.add_argument("--pg-socket", type=Path, required=True)
    p.add_argument("--pg-port", type=int, required=True)
    p.add_argument("--dbname", required=True)
    p.add_argument("--apply-rollback", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    report = execute(
        args.root, args.ref, args.pg_data, args.pg_socket, args.pg_port,
        args.dbname, apply_rollback=args.apply_rollback,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Flind isolated PostgreSQL qualification:",
              "PASS" if "blocker" not in report else "BLOCKED")
    if "blocker" in report:
        return 2
    if args.apply_rollback and not report["one_first_party_rollback_qualified"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
