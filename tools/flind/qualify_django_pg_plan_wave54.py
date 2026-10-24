#!/usr/bin/env python3
"""Read-only Django migration-plan qualification on an isolated PostgreSQL DB.

Uses the isolated PostgreSQL test cluster. This NEVER executes migrations,
touches an existing database, contacts third-party services or deploys Flind.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from urllib.parse import quote

if __package__:
    from .qualify_ephemeral_postgres import isolated_postgres
    from .qualify_django_boot_wave53 import isolated_boot_environment, diagnostic, ROOT
    from .qualify_django_lock import audit_runtime_lock
else:
    from qualify_ephemeral_postgres import isolated_postgres
    from qualify_django_boot_wave53 import isolated_boot_environment, diagnostic, ROOT
    from qualify_django_lock import audit_runtime_lock


def django_readonly_plan(port: int, password: str, name: str, timeout: int = 150) -> dict:
    environment = isolated_boot_environment()
    environment["DATABASE_URL"] = (
        f"postgresql://flind_ephemeral:{quote(password, safe='')}"
        f"@127.0.0.1:{port}/{name}?connect_timeout=3"
    )
    try:
        process = subprocess.run(
            [sys.executable, "manage.py", "showmigrations", "--plan", "--verbosity", "0"],
            cwd=ROOT, env=environment, capture_output=True,
            text=True, timeout=timeout, check=False,
        )
        output = process.stdout + process.stderr
        migration_lines = sum(
            bool(re.match(r"^\s*\[\s?[Xx ]\s?\]\s+\S+", line))
            for line in process.stdout.splitlines()
        )
        okay = process.returncode == 0 and migration_lines > 0
        result = {
            "django_migration_plan_qualified": okay,
            "django_migration_plan_entries": migration_lines,
            "schema_migrated": False,
            "release_qualified": False,
        }
        if not okay:
            result["blocker"] = diagnostic(output)
        return result
    except subprocess.TimeoutExpired:
        return {
            "django_migration_plan_qualified": False,
            "schema_migrated": False, "release_qualified": False,
            "blocker": "Django migration plan timed out",
        }
    except OSError:
        return {
            "django_migration_plan_qualified": False,
            "schema_migrated": False, "release_qualified": False,
            "blocker": "Django migration plan could not launch",
        }


def qualify_plan() -> dict:
    lock = audit_runtime_lock()
    if not lock["direct_lock_qualified"]:
        return {
            "direct_dependency_lock_qualified": False,
            "django_migration_plan_qualified": False,
            "release_qualified": False,
            "blocker": "Frozen direct dependency lock incomplete",
        }
    cluster = isolated_postgres(on_ready=django_readonly_plan)
    probe = cluster.get("django_migration_plan", {})
    return {
        "direct_dependency_lock_qualified": True,
        "isolated_postgres_passed": cluster["postgres_component_passed"],
        "django_migration_plan_qualified": bool(
            probe.get("django_migration_plan_qualified")
        ),
        "django_migration_plan_entries": probe.get("django_migration_plan_entries", 0),
        "migration_applied": False,
        "release_qualified": False,
        **({"blocker": probe["blocker"]} if "blocker" in probe else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_plan()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind isolated PostgreSQL Django migration plan: " +
              ("PASS" if result["django_migration_plan_qualified"] else "BLOCKED"))
        print("Flind migrations applied: NO; release E2E: NOT QUALIFIED")
    return 0 if result["django_migration_plan_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
