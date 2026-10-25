#!/usr/bin/env python3
"""Prove transactional CRUD on Flind's real custom session table, privately.

Requires real migrations on a fresh SCRAM-protected PostgreSQL cluster,
uses synthetic data with an explicit ROLLBACK, and qualifies no real login.
"""
from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys

if __package__:
    from .qualify_ephemeral_postgres import DEFAULT_PG_BIN_DIR, isolated_postgres
    from .qualify_auth_session_wave59 import migrate_auth_and_sessions
    from .qualify_django_lock import audit_runtime_lock
else:
    from qualify_ephemeral_postgres import DEFAULT_PG_BIN_DIR, isolated_postgres
    from qualify_auth_session_wave59 import migrate_auth_and_sessions
    from qualify_django_lock import audit_runtime_lock


def prove_session_crud(port: int, password: str, name: str) -> dict:
    """One transaction; only numeric receipts leave the private database."""
    key = "flind_wave60_" + secrets.token_hex(10)
    sql = (
        "BEGIN;"
        "INSERT INTO django_session(session_key, session_data, expire_date) "
        f"VALUES ('{key}', 'e30=', now() + interval '1 hour');"
        f"SELECT count(*) FROM django_session WHERE session_key='{key}' "
        "AND session_data='e30=';"
        "UPDATE django_session SET session_data='eyJ3YXZlIjo2MH0=' "
        f"WHERE session_key='{key}';"
        f"SELECT count(*) FROM django_session WHERE session_key='{key}' "
        "AND session_data='eyJ3YXZlIjo2MH0=';"
        f"DELETE FROM django_session WHERE session_key='{key}';"
        f"SELECT count(*) FROM django_session WHERE session_key='{key}';"
        "ROLLBACK;"
        f"SELECT count(*) FROM django_session WHERE session_key='{key}';"
    )
    env = {
        "PATH": str(DEFAULT_PG_BIN_DIR) + ":/usr/bin:/bin",
        "HOME": "/tmp", "LANG": "C",
        "PGPASSWORD": password, "PGCONNECT_TIMEOUT": "3",
    }
    args = [
        str(DEFAULT_PG_BIN_DIR / "psql"),
        "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
        "-h", "127.0.0.1", "-p", str(port),
        "-U", "flind_ephemeral", "-d", name, "-c", sql,
    ]
    base = {
        "session_crud_qualified": False,
        "session_insert_readback": False,
        "session_update_readback": False,
        "session_delete_readback": False,
        "session_rollback_readback": False,
        "release_qualified": False,
    }
    try:
        process = subprocess.run(
            args, env=env, capture_output=True, text=True, timeout=12,
            check=False,
        )
        if process.returncode:
            return {**base, "blocker": "Isolated session SQL failed"}
        # Ignore psql command tags; admit exactly four numeric SELECT receipts.
        lines = [line.strip() for line in process.stdout.splitlines()]
        rows = [int(line) for line in lines if line in ("0", "1")]
        if rows != [1, 1, 0, 0]:
            return {**base, "blocker": "Session transaction receipts mismatch"}
        return {
            **base,
            "session_crud_qualified": True,
            "session_insert_readback": True,
            "session_update_readback": True,
            "session_delete_readback": True,
            "session_rollback_readback": True,
        }
    except (OSError, subprocess.TimeoutExpired):
        return {**base, "blocker": "Isolated session SQL unavailable"}


def migrate_and_verify(port: int, password: str, name: str) -> dict:
    migration = migrate_auth_and_sessions(port, password, name)
    if not migration.get("django_framework_auth_session_qualified"):
        return {
            **migration,
            "session_crud_qualified": False,
            "blocker": migration.get("blocker") or "Required session migrations missing",
        }
    crud = prove_session_crud(port, password, name)
    return {**migration, **crud}


def qualify_session_crud() -> dict:
    if not audit_runtime_lock()["direct_lock_qualified"]:
        return {
            "session_crud_qualified": False,
            "full_schema_qualified": False,
            "release_qualified": False,
            "blocker": "Frozen Django dependency lock incomplete",
        }
    cluster = isolated_postgres(on_ready=migrate_and_verify)
    child = cluster.get("django_migration_plan") or {}
    qualified = bool(
        cluster.get("postgres_component_passed")
        and child.get("django_framework_auth_session_qualified")
        and child.get("session_crud_qualified")
    )
    return {
        "isolated_postgres_passed": bool(cluster.get("postgres_component_passed")),
        "framework_schema_qualified": bool(
            cluster.get("postgres_component_passed")
            and child.get("django_framework_auth_session_qualified")
        ),
        "session_crud_qualified": qualified,
        "session_insert_readback": bool(child.get("session_insert_readback")),
        "session_update_readback": bool(child.get("session_update_readback")),
        "session_delete_readback": bool(child.get("session_delete_readback")),
        "session_rollback_readback": bool(child.get("session_rollback_readback")),
        "custom_user_auth_qualified": False,
        "full_schema_qualified": False,
        "release_qualified": False,
        **({"blocker": child.get("blocker") or cluster.get("reason")
                       or "Session CRUD evidence incomplete"} if not qualified else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = qualify_session_crud()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Flind private session SQL CRUD: " + (
            "PASS" if report["session_crud_qualified"] else "BLOCKED"
        ))
        print("Custom user auth, complete app and release: NOT QUALIFIED")
    return 0 if report["session_crud_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
