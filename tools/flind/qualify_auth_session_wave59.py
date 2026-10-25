#!/usr/bin/env python3
"""Prove Django auth/contenttypes/session schema in ONE disposable database.

This checks framework tables only; Flind's custom user model, login, tenant
isolation and the full migration graph remain unqualified.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

if __package__:
    from .qualify_ephemeral_postgres import DEFAULT_PG_BIN_DIR, isolated_postgres
    from .qualify_isolated_migrations_wave55 import attempt_migrations
    from .qualify_django_lock import audit_runtime_lock
else:
    from qualify_ephemeral_postgres import DEFAULT_PG_BIN_DIR, isolated_postgres
    from qualify_isolated_migrations_wave55 import attempt_migrations
    from qualify_django_lock import audit_runtime_lock


MAX_STAGE_SECONDS = 155
TABLES = ("auth_group", "auth_permission", "django_session")
APPLICATIONS = ("contenttypes", "auth", "posthog_session")


def read_auth_session_receipt(port: int, password: str, name: str) -> dict:
    """Read only fixed catalog/count queries on the caller's private cluster."""
    env = {
        "PATH": str(DEFAULT_PG_BIN_DIR) + ":/usr/bin:/bin",
        "HOME": "/tmp", "LANG": "C",
        "PGPASSWORD": password, "PGCONNECT_TIMEOUT": "3",
    }
    queries = [
        f"SELECT count(*) FROM django_migrations WHERE app='{app}';"
        for app in APPLICATIONS
    ] + [
        "SELECT CASE WHEN to_regclass('public." + table +
        "') IS NOT NULL THEN 1 ELSE 0 END;"
        for table in TABLES
    ]
    command = [
        str(DEFAULT_PG_BIN_DIR / "psql"),
        "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
        "-h", "127.0.0.1", "-p", str(port),
        "-U", "flind_ephemeral", "-d", name, "-c", "".join(queries),
    ]
    zero = {
        "applied_migrations": {key: 0 for key in APPLICATIONS},
        "tables_exist": {key: False for key in TABLES},
    }
    try:
        result = subprocess.run(command, env=env, capture_output=True,
                                text=True, timeout=8, check=False)
        if result.returncode:
            return zero
        rows = [int(value.strip()) for value in result.stdout.splitlines()]
        if len(rows) != len(APPLICATIONS) + len(TABLES):
            return zero
        if any(value < 0 for value in rows[:len(APPLICATIONS)]):
            return zero
        if any(value not in (0, 1) for value in rows[len(APPLICATIONS):]):
            return zero
        return {
            "applied_migrations": dict(zip(APPLICATIONS, rows[:len(APPLICATIONS)])),
            "tables_exist": {
                table: bool(present) for table, present
                in zip(TABLES, rows[len(APPLICATIONS):])
            },
        }
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return zero


def migrate_auth_and_sessions(port: int, password: str, name: str) -> dict:
    """Stop on the first failed command, then independently verify its SQL."""
    stages = []
    reason = None
    for app in ("auth", "posthog_session"):
        step = attempt_migrations(
            port, password, name, max_seconds=MAX_STAGE_SECONDS, app_label=app,
        )
        stages.append({
            "app": app,
            "command_completed": bool(step.get("isolated_migrations_completed")),
        })
        if not step.get("isolated_migrations_completed"):
            reason = step.get("blocker") or "Scoped migration command blocked"
            break
    receipt = read_auth_session_receipt(port, password, name)
    counts = receipt["applied_migrations"]
    passed = bool(
        len(stages) == 2
        and all(stage["command_completed"] for stage in stages)
        and counts["contenttypes"] >= 2
        and counts["auth"] >= 12
        and counts["posthog_session"] >= 3
        and all(receipt["tables_exist"].values())
    )
    return {
        "django_framework_auth_session_qualified": passed,
        "custom_user_auth_qualified": False,
        "full_schema_qualified": False,
        "release_qualified": False,
        "stages": stages,
        **receipt,
        **({"blocker": reason or "Framework schema evidence incomplete"}
           if not passed else {}),
    }


def qualify_auth_session() -> dict:
    if not audit_runtime_lock()["direct_lock_qualified"]:
        return {
            "django_framework_auth_session_qualified": False,
            "custom_user_auth_qualified": False,
            "full_schema_qualified": False,
            "release_qualified": False,
            "blocker": "Frozen Django dependency lock incomplete",
        }
    cluster = isolated_postgres(on_ready=migrate_auth_and_sessions)
    result = cluster.get("django_migration_plan") or {}
    passed = bool(
        cluster.get("postgres_component_passed")
        and result.get("django_framework_auth_session_qualified")
    )
    return {
        "isolated_postgres_passed": bool(cluster.get("postgres_component_passed")),
        "django_framework_auth_session_qualified": passed,
        "custom_user_auth_qualified": False,
        "full_schema_qualified": False,
        "release_qualified": False,
        "stages": result.get("stages", []),
        "applied_migrations": result.get("applied_migrations", {}),
        "tables_exist": result.get("tables_exist", {}),
        **({"blocker": result.get("blocker") or cluster.get("reason")
                       or "Framework schema evidence incomplete"} if not passed else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = qualify_auth_session()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Flind framework auth/session schema: " + (
            "PASS" if report["django_framework_auth_session_qualified"] else "BLOCKED"
        ))
        print("Full Flind schema, custom user auth and release: NOT QUALIFIED")
    return 0 if report["django_framework_auth_session_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
