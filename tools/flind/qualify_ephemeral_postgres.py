#!/usr/bin/env python3
"""Exercise PostgreSQL in a private temporary cluster, never the shared server.

The test creates its own data directory, superuser, randomly selected local
port, test database, and transaction; all are destroyed on completion.
No Flind production migrations or application work are executed.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile

DEFAULT_PG_BIN_DIR = Path("/opt/homebrew/opt/postgresql@17/bin")
CLUSTER_USER = "flind_ephemeral"
DB_NAME = "flind_ephemeral"
MAX_START_SECONDS = 12


def choose_loopback_port() -> int:
    with socket.socket() as stream:
        stream.bind(("127.0.0.1", 0))
        return stream.getsockname()[1]


def execute(args: list[str], *, env: dict[str, str] | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout, check=False)


def pg_commands(pg_bin_dir: Path = DEFAULT_PG_BIN_DIR) -> dict[str, str]:
    binary = {}
    for name in ("initdb", "pg_ctl", "createdb", "psql"):
        path = pg_bin_dir / name
        if not path.is_file() or not os.access(path, os.X_OK):
            raise FileNotFoundError("Isolated PostgreSQL executable unavailable")
        binary[name] = str(path)
    return binary


def isolated_postgres(
    pg_bin_dir: Path = DEFAULT_PG_BIN_DIR,
    on_ready: Callable[[int, str, str], dict] | None = None,
) -> dict:
    base = {
        "postgres_component_passed": False,
        "release_qualified": False,
        "network": "127.0.0.1 only",
        "migration_qualified": False,
    }
    try:
        commands = pg_commands(pg_bin_dir)
    except OSError:
        return {**base, "reason": "Local PostgreSQL toolchain unavailable"}

    with tempfile.TemporaryDirectory(prefix="flind-postgresql-") as temporary:
        root = Path(temporary)
        cluster = root / "data"
        pwfile = root / "pw"
        pwfile.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        pwfile.chmod(0o600)
        port = choose_loopback_port()
        launch_env = {
            "PATH": str(pg_bin_dir) + ":/usr/bin:/bin",
            "HOME": temporary,
            "LANG": "C",
            "PGPASSWORD": pwfile.read_text(encoding="utf-8"),
            "PGCONNECT_TIMEOUT": "3",
        }
        started = False
        try:
            init = execute([
                commands["initdb"], "-D", str(cluster),
                "--username", CLUSTER_USER, "--auth", "scram-sha-256",
                "--pwfile", str(pwfile), "--no-instructions", "--no-sync",
                "--encoding", "UTF8", "--locale", "C",
            ], env=launch_env, timeout=35)
            if init.returncode:
                raise RuntimeError("Isolated PostgreSQL initdb failed")
            args = [
                commands["pg_ctl"], "-D", str(cluster), "-w",
                "-l", str(root / "postgres.log"), "-o",
                ("-c listen_addresses=127.0.0.1 "
                 f"-c port={port} -c unix_socket_directories={root} "
                 "-c shared_buffers=32MB -c max_connections=16 "
                 "-c fsync=off -c autovacuum=off"),
                "-t", str(MAX_START_SECONDS), "start",
            ]
            start = execute(args, env=launch_env, timeout=MAX_START_SECONDS + 7)
            if start.returncode:
                raise RuntimeError("Isolated PostgreSQL did not start")
            started = True
            host = ["-h", "127.0.0.1", "-p", str(port), "-U", CLUSTER_USER]
            version = execute(
                [commands["psql"], "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                 *host, "-d", "postgres", "-c", "SHOW server_version"],
                env=launch_env, timeout=10,
            )
            if version.returncode or not version.stdout.strip().startswith("17."):
                raise RuntimeError("PostgreSQL version query failed")
            created = execute([
                commands["createdb"], *host, "-e", DB_NAME,
            ], env=launch_env, timeout=12)
            if created.returncode:
                raise RuntimeError("Isolated test database creation failed")
            query = execute([
                commands["psql"], "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                *host, "-d", DB_NAME, "-c",
                ("BEGIN; CREATE TEMP TABLE flind_probe(id INTEGER); "
                 "INSERT INTO flind_probe VALUES (2),(5),(7); "
                 "SELECT count(*),sum(id) FROM flind_probe; ROLLBACK;"),
            ], env=launch_env, timeout=12)
            if query.returncode or "3|14" not in query.stdout.splitlines():
                raise RuntimeError("Isolated SQL transaction readback failed")
            app_probe = None
            if on_ready:
                try:
                    app_probe = on_ready(port, launch_env["PGPASSWORD"], DB_NAME)
                except Exception:
                    app_probe = {
                        "django_migration_plan_qualified": False,
                        "reason": "Django callback failed",
                    }
            return {
                **base,
                **({"django_migration_plan": app_probe} if app_probe is not None else {}),
                "postgres_component_passed": True,
                "postgres_version": version.stdout.strip(),
                "sql_rows": 3,
                "sql_sum": 14,
                "transaction_rolled_back": True,
                "temporary_database": True,
            }
        except (OSError, subprocess.TimeoutExpired, RuntimeError):
            return {**base, "reason": "Isolated PostgreSQL component test unavailable"}
        finally:
            if started or (cluster / "postmaster.pid").exists():
                stop = execute([
                    commands["pg_ctl"], "-D", str(cluster),
                    "-m", "immediate", "-w", "-t", "6", "stop",
                ], env=launch_env, timeout=10)
                if stop.returncode:
                    # Do not silently leave an isolated postgres cluster behind.
                    raise RuntimeError("Unable to terminate isolated PostgreSQL process")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = isolated_postgres()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind isolated PostgreSQL: " + (
            "PASS" if result["postgres_component_passed"] else "BLOCKED"
        ))
        print("Flind migrations and release E2E: NOT QUALIFIED")
    return 0 if result["postgres_component_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
