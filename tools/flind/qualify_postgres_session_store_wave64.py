#!/usr/bin/env python3
"""Qualify Flind's real custom Django SessionStore against private PostgreSQL.

This is storage/session behavior only. No real users, OAuth, Kafka, browser,
shared database, cloud credential or release qualification is involved.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys

if __package__:
    from .qualify_django_lock import audit_runtime_lock
    from .qualify_ephemeral_postgres import isolated_postgres
    from .qualify_auth_session_wave59 import migrate_auth_and_sessions
else:
    from qualify_django_lock import audit_runtime_lock
    from qualify_ephemeral_postgres import isolated_postgres
    from qualify_auth_session_wave59 import migrate_auth_and_sessions


def empty_receipt() -> dict:
    return {
        "session_store_postgres_qualified": False,
        "authenticated_session_created": False,
        "cross_instance_session_readback": False,
        "metadata_preserved_on_save": False,
        "invalid_user_id_unattributed": False,
        "impersonation_unattributed": False,
        "session_revocation_readback": False,
        "expired_session_unreadable": False,
        "full_schema_qualified": False,
        "real_login_qualified": False,
        "release_qualified": False,
    }


def prove_session_store(port: int, password: str, name: str) -> dict:
    """Only operate on the fresh cluster handed over by isolated_postgres."""
    receipt = empty_receipt()
    try:
        from django.conf import settings
        if settings.configured:
            return {**receipt, "blocker": "Django already configured in probe"}

        settings.configure(
            SECRET_KEY=secrets.token_urlsafe(48),
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "posthog.session.apps.PostHogSessionConfig",
            ],
            DATABASES={"default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": name,
                "USER": "flind_ephemeral",
                "PASSWORD": password,
                "HOST": "127.0.0.1",
                "PORT": str(port),
                "OPTIONS": {"connect_timeout": 3},
            }},
            SESSION_ENGINE="posthog.session.backend",
            USE_TZ=True,
        )

        # Signals belong to the full application, not this storage-only
        # disposable test; the change is process-local and not persisted.
        from posthog.session.apps import PostHogSessionConfig
        PostHogSessionConfig.ready = lambda self: None
        import django
        django.setup()

        from django.db import connections
        from django.contrib.auth import SESSION_KEY
        from posthog.session.backend import SessionStore, USER_SESSION_FLAG
        from posthog.session.models import Session

        primary = SessionStore()
        primary[SESSION_KEY] = "42"
        primary["test_marker"] = "synthetic"
        primary.create()
        key = primary.session_key
        receipt["authenticated_session_created"] = bool(
            key and Session.objects.get(session_key=key).user_id == 42
        )

        independent = SessionStore(session_key=key)
        receipt["cross_instance_session_readback"] = (
            independent.load().get("test_marker") == "synthetic"
        )

        Session.objects.filter(session_key=key).update(
            location="Local synthetic device"
        )
        primary["test_marker"] = "updated"
        primary.save()
        receipt["metadata_preserved_on_save"] = (
            Session.objects.get(session_key=key).location == "Local synthetic device"
        )

        primary[SESSION_KEY] = True
        primary.save()
        receipt["invalid_user_id_unattributed"] = (
            Session.objects.get(session_key=key).user_id is None
        )

        impersonated = SessionStore()
        impersonated[SESSION_KEY] = "43"
        impersonated[USER_SESSION_FLAG] = "synthetic-original-user"
        impersonated.create()
        receipt["impersonation_unattributed"] = (
            Session.objects.get(session_key=impersonated.session_key).user_id is None
        )

        Session.objects.filter(session_key=key).delete()
        receipt["session_revocation_readback"] = (
            SessionStore(session_key=key).load() == {}
        )

        from django.utils import timezone
        from datetime import timedelta
        Session.objects.filter(session_key=impersonated.session_key).update(
            expire_date=timezone.now() - timedelta(hours=1)
        )
        receipt["expired_session_unreadable"] = (
            SessionStore(session_key=impersonated.session_key).load() == {}
        )

        receipt["session_store_postgres_qualified"] = all(
            receipt[name] for name in (
                "authenticated_session_created",
                "cross_instance_session_readback",
                "metadata_preserved_on_save",
                "invalid_user_id_unattributed",
                "impersonation_unattributed",
                "session_revocation_readback",
                "expired_session_unreadable",
            )
        )
        if not receipt["session_store_postgres_qualified"]:
            receipt["blocker"] = "Synthetic session lifecycle receipt incomplete"
    except Exception:
        receipt["blocker"] = "Isolated Django PostgreSQL session store unavailable"
    finally:
        if "django.db" in sys.modules:
            from django.db import connections
            connections.close_all()
    return receipt


def migrate_then_probe(port: int, password: str, name: str) -> dict:
    migration = migrate_auth_and_sessions(port, password, name)
    if not migration.get("django_framework_auth_session_qualified"):
        return {
            **empty_receipt(),
            "framework_schema_qualified": False,
            "blocker": migration.get("blocker") or "Required session schema absent",
        }
    return {
        **prove_session_store(port, password, name),
        "framework_schema_qualified": True,
    }


def qualify_postgres_session_store() -> dict:
    if not audit_runtime_lock()["direct_lock_qualified"]:
        return {
            **empty_receipt(),
            "framework_schema_qualified": False,
            "blocker": "Frozen Django dependency lock incomplete",
        }
    cluster = isolated_postgres(on_ready=migrate_then_probe)
    child = cluster.get("django_migration_plan") or {}
    allowed = bool(cluster.get("postgres_component_passed"))
    qualified = bool(
        allowed
        and child.get("framework_schema_qualified")
        and child.get("session_store_postgres_qualified")
    )
    return {
        **empty_receipt(),
        **{key: child.get(key, False) for key in empty_receipt()},
        "isolated_postgres_passed": allowed,
        "framework_schema_qualified": bool(
            allowed and child.get("framework_schema_qualified")
        ),
        "session_store_postgres_qualified": qualified,
        "full_schema_qualified": False,
        "real_login_qualified": False,
        "release_qualified": False,
        **({"blocker": child.get("blocker") or cluster.get("reason")
                      or "PostgreSQL session qualification incomplete"} if not qualified else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = qualify_postgres_session_store()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Flind real PostgreSQL SessionStore: " + (
            "PASS" if report["session_store_postgres_qualified"] else "BLOCKED"
        ))
        print("Full user login, backend and product release: NOT QUALIFIED")
    return 0 if report["session_store_postgres_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
