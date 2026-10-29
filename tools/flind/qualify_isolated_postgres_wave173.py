#!/usr/bin/env python3
"""Qualify a read-only Flind migration plan and a reversible first-party smoke migration.

Use only a marked, dedicated temporary PostgreSQL cluster with Unix sockets.
Never call this on a shared DB; never infer full migration/release qualification.
"""
from __future__ import annotations
import argparse
import getpass
import hashlib
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
# Immutable first-party source approved for the ONE scoped smoke migration.
# Git blob SHA-1, verified from private Flind products/ai_training/backend.
SMOKE_MIGRATION_PATH = "products/ai_training/backend/migrations/0001_initial.py"
SMOKE_MIGRATION_GIT_BLOB = "e74ad4a9036c4118bddb3aff89f9a923b4b964ba"
# Wave223 is scoped to the original PostgreSQL 17.9-or-later major-17 cluster.
PG17_MIN_SERVER_VERSION_NUM = 170009
PG18_SERVER_VERSION_NUM = 180000


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
        # Source, cluster data and socket directories are distinct disposable
        # resources. No one may be nested under or equal to another.
        if not paths_are_pairwise_disjoint(source, data_dir, socket_dir):
            return False
        # Do not dereference a marker, Git metadata, or Unix socket that
        # redirects from owner-marked scratch to an unrelated location.
        if not scratch_entrypoints_are_not_redirected(source, data_dir, socket_dir, port):
            return False
        if (source / SOURCE_MARKER).read_text() != SOURCE_MARKER_TEXT:
            return False
        if (data_dir / PG_MARKER).read_text() != PG_MARKER_TEXT:
            return False
        if not (data_dir / "PG_VERSION").is_file():
            return False
        if (data_dir / "PG_VERSION").read_text().strip() != "17":
            return False
        if not (socket_dir / f".s.PGSQL.{port}").exists():
            return False
        return git_repository_entrypoints_are_isolated(source) and (source / "pyproject.toml").is_file()
    except (OSError, UnicodeError, ValueError):
        return False



def git_repository_entrypoints_are_isolated(root: Path) -> bool:
    """Refuse Git metadata that could redirect offline reads to another checkout."""
    git_dir = root / ".git"
    try:
        if (not git_dir.is_dir() or git_dir.is_symlink()
                or getattr(git_dir, "is_junction", lambda: False)()):
            return False
        # Git -C can read foreign Git objects through a symlinked objects/
        # directory even when .git itself and info/alternates are ordinary.
        object_store = git_dir / "objects"
        if (not object_store.is_dir() or object_store.is_symlink()
                or getattr(object_store, "is_junction", lambda: False)()):
            return False
        # Refuse redirected Git control files and object subdirectories too.
        for entry in (git_dir / "HEAD", git_dir / "config",
                      git_dir / "packed-refs", git_dir / "refs",
                      object_store / "info", object_store / "pack"):
            if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
                return False
        for redirected in (git_dir / "commondir", object_store / "info" / "alternates"):
            if redirected.exists() or redirected.is_symlink():
                return False
        # A real objects/ directory is not enough: individual pack/idx or
        # loose-object symlinks let Git resolve foreign objects without an
        # alternates file. Inspect only Git's two-level object layout, without
        # following redirected directories or reading any object contents.
        for child in object_store.iterdir():
            if child.is_symlink() or getattr(child, "is_junction", lambda: False)():
                return False
            if child.is_dir():
                for entry in child.iterdir():
                    if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
                        return False
        # Git follows physical symlinked loose refs even when .git/refs is a
        # real directory. Reject aliases at every nested ref entrypoint before
        # rev-parse or other offline Git readers can resolve foreign refs.
        refs_root = git_dir / "refs"
        if refs_root.is_dir():
            pending = [refs_root]
            inspected_refs = 0
            while pending:
                for entry in pending.pop().iterdir():
                    inspected_refs += 1
                    if (inspected_refs > 10000 or entry.is_symlink()
                            or getattr(entry, "is_junction", lambda: False)()):
                        return False
                    if entry.is_dir():
                        pending.append(entry)
        # Git -C is overridden by inherited GIT_DIR, GIT_COMMON_DIR, etc.
        if any(name.startswith("GIT_") for name in os.environ):
            return False
        return True
    except (OSError, ValueError):
        return False


def scratch_entrypoints_are_not_redirected(
    source: Path, data_dir: Path, socket_dir: Path, port: int,
) -> bool:
    """Deny symlink/junction entrypoints before reading or connecting."""
    entries = (
        source / SOURCE_MARKER, source / ".git", source / "pyproject.toml",
        data_dir / PG_MARKER, data_dir / "PG_VERSION",
        socket_dir / f".s.PGSQL.{port}",
    )
    try:
        return all(
            not entry.is_symlink()
            and not getattr(entry, "is_junction", lambda: False)()
            for entry in entries
        )
    except (OSError, ValueError):
        return False


def paths_are_pairwise_disjoint(*paths: Path) -> bool:
    """Deny overlap between a marked source, PG data and private socket path."""
    resolved = [path.resolve() for path in paths]
    for index, left in enumerate(resolved):
        for right in resolved[index + 1:]:
            if left == right or left in right.parents or right in left.parents:
                return False
    return True


def server_has_no_tcp_listeners(listen_addresses: str) -> bool:
    """A PostgreSQL empty listen_addresses setting means no TCP listeners."""
    return listen_addresses == ""


def server_uses_only_approved_socket_dir(directories: str, expected: Path) -> bool:
    """Admit exactly one expected absolute Unix-socket directory, no aliases."""
    return isinstance(directories, str) and directories == str(expected)


def django_config_matches_private_postgres(
    settings: dict, dbname: str, socket_dir: Path, port: int,
) -> bool:
    """Require canonical Django HOST/PORT and deny conflicting OPTIONS overrides."""
    if not isinstance(settings, dict) or settings.get("NAME") != dbname:
        return False
    options = settings.get("OPTIONS", {})
    if not isinstance(options, dict):
        return False
    # Django passes OPTIONS through to libpq, where dbname, hostaddr or
    # service may redirect the connection before the first server-side check.
    # Only admit the source-audited private-socket keys and bounded lock policy.
    if not set(options).issubset({"host", "port", "options"}):
        return False
    if "options" in options and options["options"] != "-c lock_timeout=20000":
        return False
    # dj_database_url parses query-string host/port into OPTIONS and leaves
    # top-level HOST/PORT empty. Both forms are used by first-party settings.
    # Missing values are allowed only if the OTHER source supplies the exact
    # private socket/port. Explicit nonempty conflicts always fail closed.
    expected_host = str(socket_dir)
    top_host = settings.get("HOST")
    option_host = options.get("host")
    if top_host not in (None, "", expected_host):
        return False
    if option_host is not None and option_host != expected_host:
        return False
    if top_host != expected_host and option_host != expected_host:
        return False
    declared_ports = (settings.get("PORT"), options.get("port"))
    if all(value in (None, "") for value in declared_ports):
        return False
    try:
        return all(
            int(value) == port for value in declared_ports
            if value not in (None, "")
        )
    except (TypeError, ValueError, OverflowError):
        return False


def is_supported_postgres_server_version(setting: object) -> bool:
    """Qualify PostgreSQL >=17.9 but reject older or different major versions."""
    try:
        number = int(setting)
    except (ValueError, TypeError, OverflowError):
        return False
    return PG17_MIN_SERVER_VERSION_NUM <= number < PG18_SERVER_VERSION_NUM


def has_pending_migration_plan(graph_qualified: bool, leaf_targets, plan) -> bool:
    """A graph alone cannot qualify an empty/no-op database migration plan."""
    return bool(graph_qualified and leaf_targets and plan)


def smoke_migration_source_matches_commit(root: Path, reader) -> bool:
    """Require both Git-committed and staged smoke source equal the pinned blob.

    MigrationExecutor can load physically staged Python before the fallback
    Git importer; pinning only the Git ref does not prove the executed file.
    """
    source = root
    for part in Path(SMOKE_MIGRATION_PATH).parts:
        source = source / part
        if source.is_symlink():
            return False
    if not source.is_file():
        return False
    try:
        committed = reader.read(SMOKE_MIGRATION_PATH)
        header = b"blob " + str(len(committed)).encode("ascii") + b"\0"
        # Git SHA-1 blob identity includes the size-prefixed object header.
        if hashlib.sha1(header + committed).hexdigest() != SMOKE_MIGRATION_GIT_BLOB:
            return False
        return source.read_bytes() == committed
    except (OSError, ImportError, ValueError):
        return False


def expected_migration(migration, plan) -> bool:
    if migration is None or migration.dependencies or len(migration.operations) != 1:
        return False
    operation = migration.operations[0]
    if type(operation).__name__ != "CreateModel":
        return False
    if any(getattr(field, "remote_field", None) for _, field in operation.fields):
        return False
    return (
        len(plan) == 1
        and plan[0][0].app_label == SMOKE_APP
        and plan[0][0].name == SMOKE_MIGRATION
        and not plan[0][1]
    )


def execute(root: Path, git_ref: str, data_dir: Path, socket_dir: Path,
            port: int, dbname: str, *, apply_rollback: bool = False) -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "isolated-postgres-flind-migration-plan",
        "django_registry_qualified": False,
        "migration_graph_qualified": False,
        "postgres_readonly_connection_qualified": False,
        "postgres_tcp_disabled_qualified": False,
        "postgres_socket_directory_qualified": False,
        "postgres_version_qualified": False,
        "migration_plan_qualified": False,
        "smoke_migration_source_qualified": False,
        "one_first_party_apply_qualified": False,
        "one_first_party_rollback_qualified": False,
        "full_migrations_qualified": False,
        "full_rollback_qualified": False,
        "release_qualified": False,
        "apply_rollback_requested": apply_rollback,
    }
    start = time.monotonic()
    # Socket restrictions are process-global; restore them even on a late
    # migration/registry exception so a caller cannot inherit a broken socket API.
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection
    original_sys_path = list(sys.path)
    previous_env: dict[str, str | None] = {}
    finder = None
    connection = None
    previous_alarm: int | None = None
    try:
        if not safe_locations(root, data_dir, socket_dir, port, dbname):
            raise ValueError("unsafe_database_or_source_target")
        # Never replace and later discard another caller's process alarm.
        # An existing timer is an unsafe global ownership conflict.
        previous_alarm = signal.alarm(150)
        if previous_alarm:
            raise ValueError("existing_process_alarm")
        isolated_env = {
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
        }
        previous_env = {key: os.environ.get(key) for key in isolated_env}
        os.environ.update(isolated_env)
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
        # Freeze every Git-tree lookup and import to the resolved immutable commit.
        # A symbolic branch may move while Django is importing migrations.
        tracked = index_tracked_python(root, sha)
        ready, count = graph_source_ready(root, tracked)
        if not ready:
            raise ValueError("migration_source_tree_incomplete")
        report["migration_files_staged"] = count
        sock_path = str(socket_dir / f".s.PGSQL.{port}")
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
        with GitBlobBatchReader(root, sha) as reader:
            finder = GitTrackedPythonFinder(
                root, sha, tracked, limit=2600, deadline=140, batch_reader=reader,
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
            if not django_config_matches_private_postgres(
                settings, dbname, socket_dir, port,
            ):
                raise ValueError("unexpected_django_postgres_config")
            with connection.cursor() as cursor:
                cursor.execute("SET default_transaction_read_only = on")
                cursor.execute("SELECT current_database(), inet_server_addr() IS NULL")
                actual_db, unix_socket = cursor.fetchone()
                cursor.execute("SHOW data_directory")
                actual_data_dir = Path(cursor.fetchone()[0]).resolve()
                cursor.execute("SHOW default_transaction_read_only")
                read_only = cursor.fetchone()[0] == "on"
                cursor.execute("SHOW listen_addresses")
                listen_addresses = cursor.fetchone()[0]
                cursor.execute("SHOW unix_socket_directories")
                unix_socket_directories = cursor.fetchone()[0]
                cursor.execute("SHOW server_version_num")
                server_version_num = cursor.fetchone()[0]
            if (actual_db != dbname or not unix_socket or not read_only
                    or actual_data_dir != data_dir.resolve()
                    or not server_has_no_tcp_listeners(listen_addresses)
                    or not server_uses_only_approved_socket_dir(
                        unix_socket_directories, socket_dir
                    )
                    or not is_supported_postgres_server_version(server_version_num)):
                raise ValueError("postgres_isolation_not_verified")
            report["postgres_readonly_connection_qualified"] = True
            report["postgres_tcp_disabled_qualified"] = True
            report["postgres_socket_directory_qualified"] = True
            report["postgres_version_qualified"] = True
            executor = MigrationExecutor(connection)
            report["migration_graph_nodes"] = len(executor.loader.graph.nodes)
            report["disk_migrations"] = len(executor.loader.disk_migrations)
            report["migration_graph_qualified"] = bool(report["migration_graph_nodes"] and report["disk_migrations"])
            leaf_targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(leaf_targets)
            report["migration_plan_qualified"] = has_pending_migration_plan(
                report["migration_graph_qualified"], leaf_targets, plan,
            )
            report["planned_migrations"] = len(plan)
            report["leaf_targets"] = len(leaf_targets)
            if not report["migration_plan_qualified"]:
                raise ValueError("no_pending_original_migration_plan")

            if apply_rollback:
                if not smoke_migration_source_matches_commit(root, reader):
                    raise ValueError("first_party_smoke_source_not_pinned")
                report["smoke_migration_source_qualified"] = True
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
    except Exception as exc:
        report["blocker"] = type(exc).__name__
        # A missing Python dependency is actionable, but arbitrary exception
        # messages may contain credentials or filesystem details. Record only
        # a bounded Python module identifier, never str(exc) or a traceback.
        if isinstance(exc, ModuleNotFoundError):
            module_name = exc.name
            if (isinstance(module_name, str) and
                    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", module_name)):
                report["missing_python_module"] = module_name
    finally:
        # Close the actual Django DB session on success OR refusal. Leave the
        # Unix-only socket policy installed until its connection is closed.
        if connection is not None:
            try:
                connection.close()
            except Exception as close_error:
                report.setdefault("blocker", type(close_error).__name__)
        # Restore the original socket API regardless of success, refusal or error.
        # The deny-TCP policy remains active throughout all Django/PG operations.
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex
        socket.create_connection = original_create_connection
        # The source finder, import paths and synthetic service URLs must not
        # escape this invocation, particularly after a late Django failure.
        if finder is not None and finder in sys.meta_path:
            sys.meta_path.remove(finder)
        sys.path[:] = original_sys_path
        for key, old in previous_env.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        report["elapsed_seconds"] = round(time.monotonic() - start, 1)
        # Do not cancel another caller's alarm when admission failed before
        # ours was installed. An existing timer was refused and restored.
        if previous_alarm is not None:
            signal.alarm(previous_alarm)
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
    required = (
        "django_registry_qualified", "migration_graph_qualified",
        "postgres_readonly_connection_qualified", "postgres_tcp_disabled_qualified",
        "postgres_socket_directory_qualified", "postgres_version_qualified",
        "migration_plan_qualified",
    )
    qualified = (
        "blocker" not in report
        and all(report.get(field) is True for field in required)
        and (not args.apply_rollback or (
            report.get("smoke_migration_source_qualified") is True
            and report.get("one_first_party_apply_qualified") is True
            and report.get("one_first_party_rollback_qualified") is True
        ))
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Flind isolated PostgreSQL qualification:",
              "PASS" if qualified else "BLOCKED")
    return 0 if qualified else 2


if __name__ == "__main__":
    sys.exit(main())
