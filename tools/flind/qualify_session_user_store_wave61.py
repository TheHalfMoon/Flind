#!/usr/bin/env python3
"""Exercise Flind's REAL custom Django session store in memory, no network.

This is a focused session lifecycle proof, not a production backend test:
no full-schema migrations, real users, OAuth or persistent databases.
"""
from __future__ import annotations

import argparse
import json
import sys


def qualify_store() -> dict[str, bool]:
    base = {
        "real_django_store_qualified": False,
        "authenticated_session_created": False,
        "invalid_user_id_unattributed": False,
        "impersonation_unattributed": False,
        "update_clears_invalid_attribution": False,
        "display_metadata_preserved": False,
        "sqlite_memory_only": True,
        "custom_user_login_qualified": False,
        "full_schema_qualified": False,
        "release_qualified": False,
    }
    try:
        from django.conf import settings

        if settings.configured:
            return {**base, "blocker": "Django already configured"}
        settings.configure(
            SECRET_KEY="wave61-isolated-session-smoke-no-deploy",
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "posthog.session.apps.PostHogSessionConfig",
            ],
            DATABASES={"default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }},
            SESSION_ENGINE="posthog.session.backend",
            USE_TZ=True,
        )
        from posthog.session.apps import PostHogSessionConfig
        # This isolated schema/store probe must never start app signals, jobs
        # or provider integrations. Do not alter production's AppConfig.
        PostHogSessionConfig.ready = lambda self: None
        import django
        django.setup()

        from django.db import connection
        from posthog.session.backend import SESSION_KEY, USER_SESSION_FLAG, SessionStore
        from posthog.session.models import Session
        with connection.schema_editor() as schema:
            schema.create_model(Session)

        authenticated = SessionStore()
        authenticated[SESSION_KEY] = "42"
        authenticated.create()
        created = Session.objects.get(session_key=authenticated.session_key)
        base["authenticated_session_created"] = created.user_id == 42

        invalid = SessionStore()
        invalid[SESSION_KEY] = True
        invalid.create()
        base["invalid_user_id_unattributed"] = (
            Session.objects.get(session_key=invalid.session_key).user_id is None
        )

        impersonated = SessionStore()
        impersonated[SESSION_KEY] = "43"
        impersonated[USER_SESSION_FLAG] = "original-user"
        impersonated.create()
        base["impersonation_unattributed"] = (
            Session.objects.get(session_key=impersonated.session_key).user_id is None
        )

        Session.objects.filter(session_key=authenticated.session_key).update(
            location="Synthetic local device",
        )
        authenticated[SESSION_KEY] = True
        authenticated.save()
        updated = Session.objects.get(session_key=authenticated.session_key)
        base["update_clears_invalid_attribution"] = updated.user_id is None
        base["display_metadata_preserved"] = (
            updated.location == "Synthetic local device"
        )
        base["real_django_store_qualified"] = all([
            base["authenticated_session_created"],
            base["invalid_user_id_unattributed"],
            base["impersonation_unattributed"],
            base["update_clears_invalid_attribution"],
            base["display_metadata_preserved"],
        ])
    except Exception:
        return {**base, "blocker": "Isolated Django session store unavailable"}
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_store()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind real in-memory session store: " + (
            "PASS" if result["real_django_store_qualified"] else "BLOCKED"
        ))
        print("Full backend and release: NOT QUALIFIED")
    return 0 if result["real_django_store_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
