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

# Django's own migration progress lines only. Never include raw application
# logs, SQL, URLs or exception bodies in any outward diagnostic receipt.
MIGRATION_LINE = re.compile(
    r"(?m)^[ \t]*Applying ([A-Za-z_][A-Za-z0-9_]{0,79}\.[A-Za-z0-9_]{1,120})"
    r"\.\.\.[ \t]*(OK|FAKED)?[ \t]*\r?$"
)


def migration_console_progress(output: str) -> dict[str, str | None]:
    """Bounded sanitized migration labels; no log text or credentials."""
    attempted = None
    completed = None
    for match in MIGRATION_LINE.finditer(output[-18_000:]):
        attempted = match.group(1)
        if match.group(2) in ("OK", "FAKED"):
            completed = attempted
    return {
        "last_attempted_migration": attempted,
        "last_console_completed_migration": completed,
        "interrupted_migration": attempted if attempted != completed else None,
    }


def summarize_migration_log(log) -> tuple[str, bool]:
    """Keep a small safe diagnostic tail but scan *all* lines for stage marker.

    Django prints 'Running migrations:' only once at the beginning. A
    long-running 360-second command can push it thousands of lines out
    of the tail even when thousands of real migrations were committed.
    The stage bit must not accidentally report a startup failure then.
    """
    log.seek(0)
    tail = deque(maxlen=180)
    django_migration_stage_seen = False
    for line in log:
        if line.strip() == "Running migrations:":
            django_migration_stage_seen = True
        tail.append(line)
    return "".join(tail)[-18_000:], django_migration_stage_seen


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
    if app_label not in (None, "contenttypes", "auth", "posthog_session"):
        raise ValueError("Only explicitly allowlisted Django core-app scoping is supported")
    # Unbuffered Django progress lines make an interrupted migration visible
    # without exporting raw logs or touching another database.
    cmd = [sys.executable, "-u", "manage.py", "migrate"]
    if app_label:
        cmd.append(app_label)
    cmd.extend(["--noinput", "--database", "default", "--verbosity", "1"])
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
        # Scan for the exact one-time stage marker across the entire log.
        # Still retain ONLY the last 180 lines for sanitized diagnostics.
        output, stage_seen = summarize_migration_log(log)
        progress = migration_console_progress(output)
        safe_class = diagnostic(output)
        succeeded = process.returncode == 0 and reason is None and applied > 0
        result = {
            "isolated_migrations_completed": succeeded,
            "migration_rows_applied_to_disposable_db": applied,
            "last_committed_migration": last,
            "django_console_output_seen": bool(output.strip()),
            "django_migration_stage_seen": stage_seen,
            "django_error_class": (
                safe_class if safe_class != "No recognized exception class" else None
            ),
            "live_project_schema_untouched": True,
            "release_qualified": False,
            **progress,
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
        "last_attempted_migration": probe.get("last_attempted_migration"),
        "last_console_completed_migration": probe.get("last_console_completed_migration"),
        "interrupted_migration": probe.get("interrupted_migration"),
        "django_console_output_seen": probe.get("django_console_output_seen"),
        "django_migration_stage_seen": probe.get("django_migration_stage_seen"),
        "django_error_class": probe.get("django_error_class"),
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
