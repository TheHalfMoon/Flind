#!/usr/bin/env python3
"""Bounded, progress-aware real Django migrations on ONE ephemeral database.

Retries may use already committed migrations; NO shared PostgreSQL service,
paid cloud, migrations faker, bypass or persistent user database is involved.
"""
from __future__ import annotations

import argparse
import json
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
MAX_SECONDS_PER_ROUND = 120


def run_resumable(
    port: int, password: str, name: str, *,
    max_rounds: int = 2,
    seconds_per_round: int = MAX_SECONDS_PER_ROUND,
) -> dict:
    if not 1 <= max_rounds <= MAX_ROUNDS:
        raise ValueError("Unsupported number of bounded rounds")
    if not 20 <= seconds_per_round <= MAX_SECONDS_PER_ROUND:
        raise ValueError("Unsupported per-round time limit")

    progress = []
    previous_count = 0
    completed = False
    reason = "No migration rounds completed"
    for index in range(max_rounds):
        result = attempt_migrations(
            port, password, name, max_seconds=seconds_per_round,
        )
        count = result.get("migration_rows_applied_to_disposable_db", 0)
        if not isinstance(count, int) or count < previous_count:
            reason = "Migration receipt count invalid or regressed"
            break
        progress.append({
            "round": index + 1,
            "committed_migration_rows": count,
            "newly_committed_rows": count - previous_count,
            "last_committed_migration": result.get("last_committed_migration"),
            "command_completed": bool(result.get("isolated_migrations_completed")),
        })
        if result.get("isolated_migrations_completed"):
            completed = True
            reason = ""
            break
        if count == previous_count:
            reason = "No new committed migration progress"
            break
        if result.get("blocker") != "Migration time limit reached":
            reason = result.get("blocker") or "Migration command blocked"
            break
        previous_count = count
        reason = "Bounded migration rounds exhausted"

    return {
        "full_schema_migrations_completed": completed,
        "rounds_executed": len(progress),
        "migration_progress": progress,
        "migration_committed_rows_total": progress[-1]["committed_migration_rows"] if progress else 0,
        "release_qualified": False,
        "temporary_database": True,
        **({"blocker": reason} if reason else {}),
    }


def qualify_resumable(
    rounds: int = 2,
    seconds: int = MAX_SECONDS_PER_ROUND,
) -> dict:
    if not 1 <= rounds <= MAX_ROUNDS or not 20 <= seconds <= MAX_SECONDS_PER_ROUND:
        raise ValueError("Out-of-range migration guard")
    if not audit_runtime_lock()["direct_lock_qualified"]:
        return {
            "full_schema_migrations_completed": False,
            "release_qualified": False,
            "blocker": "Frozen Python dependency lock incomplete",
        }
    cluster = isolated_postgres(
        on_ready=lambda port, password, name: run_resumable(
            port, password, name, max_rounds=rounds, seconds_per_round=seconds,
        ),
    )
    child = cluster.get("django_migration_plan", {})
    return {
        "isolated_postgres_passed": bool(cluster["postgres_component_passed"]),
        "full_schema_migrations_completed": bool(
            cluster["postgres_component_passed"]
            and child.get("full_schema_migrations_completed")
        ),
        "rounds_executed": child.get("rounds_executed", 0),
        "migration_committed_rows_total": child.get("migration_committed_rows_total", 0),
        "migration_progress": child.get("migration_progress", []),
        "release_qualified": False,
        **({"blocker": child["blocker"]} if child.get("blocker") else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--seconds", type=int, default=MAX_SECONDS_PER_ROUND)
    args = parser.parse_args(argv)
    if not 1 <= args.rounds <= MAX_ROUNDS or not 20 <= args.seconds <= MAX_SECONDS_PER_ROUND:
        parser.error("Allowed: --rounds 1..3, --seconds 20..120")
    report = qualify_resumable(args.rounds, args.seconds)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Flind isolated full schema: " + (
            "PASS" if report["full_schema_migrations_completed"] else "BLOCKED"
        ))
        print("Release E2E: NOT QUALIFIED")
    return 0 if report["full_schema_migrations_completed"] else 2


if __name__ == "__main__":
    sys.exit(main())
