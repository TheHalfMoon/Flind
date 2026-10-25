#!/usr/bin/env python3
"""Bounded sustained, un-faked Django migration qualification on private PG.

Allows 1–3 longer subprocess lifetimes to reduce Django graph boot/reparse
overhead. Never writes to an existing database or removes migration steps.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys

if __package__:
    from .qualify_isolated_migrations_wave55 import attempt_migrations
    from .qualify_ephemeral_postgres import isolated_postgres
    from .qualify_django_lock import audit_runtime_lock
else:
    from qualify_isolated_migrations_wave55 import attempt_migrations
    from qualify_ephemeral_postgres import isolated_postgres
    from qualify_django_lock import audit_runtime_lock


MAX_ROUNDS = 3
MAX_SECONDS = 360
MIN_SECONDS = 60
MIN_FREE_GIB = 10.0


def admitted(rounds: int, seconds: int) -> bool:
    return (
        type(rounds) is int and type(seconds) is int
        and 1 <= rounds <= MAX_ROUNDS
        and MIN_SECONDS <= seconds <= MAX_SECONDS
    )


def run_sustained(
    port: int, password: str, db_name: str, *,
    rounds: int, seconds: int,
) -> dict:
    if not admitted(rounds, seconds):
        raise ValueError("Out of bounds sustained migration request")
    history: list[dict] = []
    previous = 0
    complete = False
    blocker = "Bounded sustained migration rounds exhausted"

    for index in range(rounds):
        result = attempt_migrations(
            port, password, db_name, max_seconds=seconds,
        )
        count = result.get("migration_rows_applied_to_disposable_db")
        if type(count) is not int or count < previous:
            blocker = "Committed migration count missing or regressed"
            break
        completed = bool(result.get("isolated_migrations_completed"))
        safe = {
            "round": index + 1,
            "committed_rows": count,
            "new_rows": count - previous,
            "completed": completed,
            "last_committed_migration": result.get("last_committed_migration"),
            "last_attempted_migration": result.get("last_attempted_migration"),
            "django_stage_seen": bool(result.get("django_migration_stage_seen")),
            "django_error_class": result.get("django_error_class"),
        }
        history.append(safe)
        if completed and count == 0:
            blocker = "Migration command reported success without committed schema"
            break
        if completed:
            complete = True
            blocker = ""
            break
        if result.get("django_error_class") is not None:
            blocker = "Django reported an error; no automatic restart permitted"
            break
        if result.get("blocker") != "Migration time limit reached":
            blocker = "Migration command failed before time bound"
            break
        if count == previous:
            blocker = (
                "Django startup did not reach migration stage"
                if not result.get("django_migration_stage_seen")
                else "No new committed migration rows"
            )
            break
        previous = count

    return {
        "full_schema_migrations_completed": complete,
        "temporary_database": True,
        "rounds_executed": len(history),
        "committed_migration_rows": history[-1]["committed_rows"] if history else 0,
        "round_progress": history,
        "release_qualified": False,
        **({"blocker": blocker} if blocker else {}),
    }


def qualify_sustained(rounds: int = 1, seconds: int = MAX_SECONDS) -> dict:
    if not admitted(rounds, seconds):
        raise ValueError("Out-of-bounds migration time or rounds")
    # Up-front disk admission; the underlying attempt also checks throughout
    # and stops the whole subprocess group before going below its safety floor.
    try:
        free_gib = shutil.disk_usage("/tmp").free / (1024 ** 3)
    except OSError:
        free_gib = 0.0
    if free_gib < MIN_FREE_GIB:
        return {
            "full_schema_migrations_completed": False,
            "release_qualified": False,
            "blocker": "10 GiB free temporary-disk reserve required",
        }

    if not audit_runtime_lock().get("direct_lock_qualified"):
        return {
            "full_schema_migrations_completed": False,
            "release_qualified": False,
            "blocker": "Exact Python runtime dependency lock incomplete",
        }

    cluster = isolated_postgres(
        on_ready=lambda port, password, name: run_sustained(
            port, password, name, rounds=rounds, seconds=seconds,
        ),
    )
    child = cluster.get("django_migration_plan") or {}
    postgres_ok = bool(cluster.get("postgres_component_passed"))
    completed = bool(
        postgres_ok and child.get("full_schema_migrations_completed")
    )
    return {
        "isolated_postgres_passed": postgres_ok,
        "full_schema_migrations_completed": completed,
        "rounds_executed": child.get("rounds_executed", 0),
        "committed_migration_rows": child.get("committed_migration_rows", 0),
        "round_progress": child.get("round_progress", []),
        "temporary_database": True,
        "release_qualified": False,
        **({"blocker": child.get("blocker", "Private PostgreSQL attempt unavailable")}
           if not completed else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--seconds", type=int, default=MAX_SECONDS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not admitted(args.rounds, args.seconds):
        parser.error("Require --rounds 1..3 and --seconds 60..360")
    receipt = qualify_sustained(args.rounds, args.seconds)
    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print("Private full Django schema:",
              "PASS" if receipt["full_schema_migrations_completed"] else "BLOCKED")
        print("Flind release: NOT QUALIFIED")
    return 0 if receipt["full_schema_migrations_completed"] else 2


if __name__ == "__main__":
    sys.exit(main())
