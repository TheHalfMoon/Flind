#!/usr/bin/env python3
"""Qualify *actual* Django contenttypes schema on a private test database only.

This is a scoped migration smoke, NOT Flind's full migration or E2E qualification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

if __package__:
    from .qualify_ephemeral_postgres import isolated_postgres, DEFAULT_PG_BIN_DIR
    from .qualify_isolated_migrations_wave55 import attempt_migrations
    from .qualify_django_lock import audit_runtime_lock
else:
    from qualify_ephemeral_postgres import isolated_postgres, DEFAULT_PG_BIN_DIR
    from qualify_isolated_migrations_wave55 import attempt_migrations
    from qualify_django_lock import audit_runtime_lock


MAX_CORE_SECONDS = 155


def core_schema_receipt(port: int, password: str, name: str) -> dict:
    """SQL only on the disposable PostgreSQL instance; no user schema."""
    env = {
        "PATH": str(DEFAULT_PG_BIN_DIR) + ":/usr/bin:/bin",
        "HOME": "/tmp", "LANG": "C",
        "PGPASSWORD": password, "PGCONNECT_TIMEOUT": "3",
    }
    command = [
        str(DEFAULT_PG_BIN_DIR / "psql"),
        "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
        "-h", "127.0.0.1", "-p", str(port),
        "-U", "flind_ephemeral", "-d", name, "-c",
        (
            "SELECT count(*) FROM django_migrations "
            "WHERE app='contenttypes';"
            "SELECT CASE WHEN to_regclass('public.django_content_type') "
            "IS NOT NULL THEN 1 ELSE 0 END;"
        ),
    ]
    try:
        result = subprocess.run(
            command, env=env, capture_output=True, text=True, timeout=8,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError("Scoped schema query failed")
        numbers = [int(line.strip()) for line in result.stdout.splitlines()]
        if len(numbers) != 2:
            raise ValueError("Invalid schema query response")
        return {
            "contenttypes_applied_migrations": numbers[0],
            "django_content_type_table_exists": numbers[1] == 1,
        }
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {
            "contenttypes_applied_migrations": 0,
            "django_content_type_table_exists": False,
        }


def migrate_core_schema(port: int, password: str, name: str) -> dict:
    migrated = attempt_migrations(
        port, password, name,
        max_seconds=MAX_CORE_SECONDS,
        app_label="contenttypes",
    )
    receipt = core_schema_receipt(port, password, name)
    passed = bool(
        migrated.get("isolated_migrations_completed")
        and receipt["contenttypes_applied_migrations"] >= 2
        and receipt["django_content_type_table_exists"]
    )
    return {
        "core_schema_qualified": passed,
        "full_schema_qualified": False,
        "release_qualified": False,
        **receipt,
        **({"blocker": migrated["blocker"]} if "blocker" in migrated else {}),
    }


def qualify_core_schema() -> dict:
    lock = audit_runtime_lock()
    if not lock["direct_lock_qualified"]:
        return {
            "core_schema_qualified": False,
            "release_qualified": False,
            "blocker": "Frozen Django dependency lock incomplete",
        }
    cluster = isolated_postgres(on_ready=migrate_core_schema)
    application = cluster.get("django_migration_plan", {})
    return {
        "core_schema_qualified": bool(application.get("core_schema_qualified")),
        "isolated_postgres_passed": cluster["postgres_component_passed"],
        "django_content_type_table_exists":
            bool(application.get("django_content_type_table_exists")),
        "contenttypes_applied_migrations":
            application.get("contenttypes_applied_migrations", 0),
        "full_schema_qualified": False,
        "release_qualified": False,
        **({"blocker": application["blocker"]} if "blocker" in application else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_core_schema()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind Django core contenttypes schema: " +
              ("PASS" if result["core_schema_qualified"] else "BLOCKED"))
        print("Full Flind schema and release E2E: NOT QUALIFIED")
    return 0 if result["core_schema_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
