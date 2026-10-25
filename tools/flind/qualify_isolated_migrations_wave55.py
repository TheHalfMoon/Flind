#!/usr/bin/env python3
"""Attempt real Django migrations on a disposable, private PostgreSQL cluster.

No live/shared DB access or inherited app credentials. Abort if free disk
drops below a safety threshold. Results are diagnostic, NOT release E2E.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

if __package__:
    from .qualify_ephemeral_postgres import isolated_postgres, DEFAULT_PG_BIN_DIR
    from .qualify_django_boot_wave53 import isolated_boot_environment, ROOT, diagnostic
    from .qualify_django_lock import audit_runtime_lock
else:
    from qualify_ephemeral_postgres import isolated_postgres, DEFAULT_PG_BIN_DIR
    from qualify_django_boot_wave53 import isolated_boot_environment, ROOT, diagnostic
    from qualify_django_lock import audit_runtime_lock


MIN_FREE_GIB = 2.5
MAX_MIGRATION_SECONDS = 360


def read_applied_count(port: int, password: str, name: str) -> int:
    env = {
        "PATH": str(DEFAULT_PG_BIN_DIR) + ":/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C",
        "PGPASSWORD": password,
        "PGCONNECT_TIMEOUT": "3",
    }
    pg_cmd = [
        str(DEFAULT_PG_BIN_DIR / "psql"), "-X", "-A", "-t",
        "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(port),
        "-U", "flind_ephemeral", "-d", name, "-c",
        "SELECT count(*) FROM django_migrations",
    ]
    try:
        p = subprocess.run(pg_cmd, env=env, capture_output=True,
                           text=True, timeout=4, check=False)
        return int(p.stdout.strip()) if p.returncode == 0 else 0
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return 0


def read_last_migration(port: int, password: str, name: str) -> str | None:
    """Identify the last committed migration in the disposable DB only."""
    env = {
        "PATH": str(DEFAULT_PG_BIN_DIR) + ":/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C",
        "PGPASSWORD": password,
        "PGCONNECT_TIMEOUT": "3",
    }
    command = [
        str(DEFAULT_PG_BIN_DIR / "psql"), "-X", "-A", "-t",
        "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(port),
        "-U", "flind_ephemeral", "-d", name, "-c",
        "SELECT app, name FROM django_migrations ORDER BY id DESC LIMIT 1",
    ]
    try:
        result = subprocess.run(command, env=env, capture_output=True,
                                text=True, timeout=4, check=False)
        if result.returncode != 0:
            return None
        last = result.stdout.strip().replace("|", ".")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", last):
            return None
        return last
    except (OSError, subprocess.TimeoutExpired):
        return None


def attempt_migrations(
    port: int, password: str, name: str, *,
    max_seconds: int = MAX_MIGRATION_SECONDS,
    app_label: str | None = None,
) -> dict:
    env = isolated_boot_environment()
    env["DATABASE_URL"] = (
        f"postgresql://flind_ephemeral:{quote(password, safe='')}"
        f"@127.0.0.1:{port}/{name}?connect_timeout=3"
    )
    env.update({
        "CLICKHOUSE_HOST": "127.0.0.1",
        "CLICKHOUSE_PORT": "65435",
        "CLICKHOUSE_HTTP_PORT": "65436",
        "KAFKA_HOSTS": "127.0.0.1:65437",
    })
    if app_label not in (None, "contenttypes"):
        raise ValueError("Only bounded core-schema scoping is supported")
    cmd = [sys.executable, "manage.py", "migrate"]
    if app_label:
        cmd.append(app_label)
    cmd.extend(["--noinput", "--database", "default", "--verbosity", "0"])
    with tempfile.TemporaryFile(mode="w+t") as log:
        process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic()
        reason = None
        while process.poll() is None:
            elapsed = time.monotonic() - started
            free_gib = shutil.disk_usage("/tmp").free / (1024 ** 3)
            if free_gib < MIN_FREE_GIB:
                reason = "Disk safety threshold reached"
            elif elapsed > max_seconds:
                reason = "Migration time limit reached"
            if reason:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=7)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=7)
                break
            time.sleep(1)
        applied = read_applied_count(port, password, name)
        last = read_last_migration(port, password, name) if applied else None
        log.seek(0)
        # Use the tail so any final migration error is not hidden by boot logs.
        output = "".join(deque(log, maxlen=180))[-18_000:]
        succeeded = process.returncode == 0 and reason is None and applied > 0
        result = {
            "isolated_migrations_completed": succeeded,
            "migration_rows_applied_to_disposable_db": applied,
            "last_committed_migration": last,
            "live_project_schema_untouched": True,
            "release_qualified": False,
        }
        if not succeeded:
            result["blocker"] = reason or diagnostic(output)
        return result


def qualify_isolated_migrations(max_seconds: int = MAX_MIGRATION_SECONDS) -> dict:
    lock = audit_runtime_lock()
    if not lock["direct_lock_qualified"]:
        return {
            "direct_dependency_lock_qualified": False,
            "isolated_migrations_completed": False,
            "release_qualified": False,
            "blocker": "Frozen dependency lock incomplete",
        }
    cluster = isolated_postgres(
        on_ready=lambda port, password, name: attempt_migrations(
            port, password, name, max_seconds=max_seconds,
        ),
    )
    probe = cluster.get("django_migration_plan", {})
    return {
        "direct_dependency_lock_qualified": True,
        "isolated_postgres_passed": cluster["postgres_component_passed"],
        "isolated_migrations_completed": bool(
            probe.get("isolated_migrations_completed")
        ),
        "migration_rows_applied_to_disposable_db":
            probe.get("migration_rows_applied_to_disposable_db", 0),
        "last_committed_migration": probe.get("last_committed_migration"),
        "live_project_schema_untouched": True,
        "release_qualified": False,
        **({"blocker": probe["blocker"]} if "blocker" in probe else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=MAX_MIGRATION_SECONDS)
    args = parser.parse_args(argv)
    if not 20 <= args.max_seconds <= MAX_MIGRATION_SECONDS:
        parser.error("--max-seconds must be between 20 and 360")
    result = qualify_isolated_migrations(args.max_seconds)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind isolated Django migrations: " + (
            "PASS" if result["isolated_migrations_completed"] else "BLOCKED"
        ))
        print("Flind release E2E: NOT QUALIFIED")
    return 0 if result["isolated_migrations_completed"] else 2


if __name__ == "__main__":
    sys.exit(main())
