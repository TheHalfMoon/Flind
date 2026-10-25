#!/usr/bin/env python3
"""Real HTTPS-like Django Client login/CSRF/session integration on private PostgreSQL.

Exercises Flind's actual SessionStore and Django's actual auth/session/CSRF
middleware against a disposable PostgreSQL instance. Uses framework auth.User,
NOT the production Flind custom User or production middleware/URL routing.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
import json
import secrets
import sys
from types import ModuleType

if __package__:
    from .qualify_django_lock import audit_runtime_lock
    from .qualify_ephemeral_postgres import isolated_postgres
    from .qualify_auth_session_wave59 import migrate_auth_and_sessions
else:
    from qualify_django_lock import audit_runtime_lock
    from qualify_ephemeral_postgres import isolated_postgres
    from qualify_auth_session_wave59 import migrate_auth_and_sessions


FLAGS = (
    "auth_csrf_missing_rejected",
    "auth_hostile_origin_rejected",
    "bad_password_rejected",
    "password_login_http_accepted",
    "flind_session_user_id_stamped",
    "unrelated_client_stays_anonymous",
    "two_user_sessions_separated",
    "unsafe_logout_without_csrf_rejected",
    "logout_revokes_http_session",
    "expired_session_unreadable_via_http",
)


def blocked(message: str) -> dict:
    return {
        **{k: False for k in FLAGS},
        "framework_http_login_flind_sessionstore_qualified": False,
        "flind_custom_user_login_qualified": False,
        "production_middleware_stack_qualified": False,
        "product_oauth_qualified": False,
        "tenant_authorization_qualified": False,
        "browser_playwright_qualified": False,
        "release_qualified": False,
        "blocker": message,
    }


def prove_django_http_login(port: int, password: str, db_name: str) -> dict:
    result = blocked("Private framework HTTP session proof incomplete")
    try:
        from django.conf import settings
        if settings.configured:
            return blocked("Django settings unexpectedly configured before probe")
        settings.configure(
            SECRET_KEY=secrets.token_urlsafe(48),
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "posthog.session.apps.PostHogSessionConfig",
            ],
            DATABASES={"default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": db_name, "USER": "flind_ephemeral",
                "PASSWORD": password, "HOST": "127.0.0.1",
                "PORT": str(port), "OPTIONS": {"connect_timeout": 3},
            }},
            SESSION_ENGINE="posthog.session.backend",
            MIDDLEWARE=[
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
            ],
            AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
            ROOT_URLCONF="_flind_wave104_private_http_urls",
            ALLOWED_HOSTS=["testserver"],
            CSRF_COOKIE_SECURE=True,
            SESSION_COOKIE_SECURE=True,
            USE_TZ=True,
        )
        # Full product signals use many independent services; for this
        # disposable framework auth slice, preserve Wave64's scoped bypass.
        from posthog.session.apps import PostHogSessionConfig
        PostHogSessionConfig.ready = lambda self: None
        import django
        django.setup()

        from django.contrib.auth import authenticate, login, logout
        from django.contrib.auth.models import User
        from django.db import connection
        from django.http import JsonResponse, HttpResponseNotAllowed
        from django.test import Client
        from django.urls import path
        from django.utils import timezone
        from django.views.decorators.csrf import ensure_csrf_cookie
        from posthog.session.models import Session

        @ensure_csrf_cookie
        def csrf(request):
            return JsonResponse({"csrf": True})

        def sign_in(request):
            if request.method != "POST":
                return HttpResponseNotAllowed(["POST"])
            user = authenticate(request, username=request.POST.get("username"),
                                password=request.POST.get("password"))
            if user is None:
                return JsonResponse({"authenticated": False}, status=401)
            login(request, user)
            return JsonResponse({"authenticated": True})

        def whoami(request):
            user = request.user
            return JsonResponse({"authenticated": bool(user.is_authenticated),
                                 "user_id": user.pk if user.is_authenticated else None})

        def sign_out(request):
            if request.method != "POST":
                return HttpResponseNotAllowed(["POST"])
            logout(request)
            return JsonResponse({"logged_out": True})

        urls = ModuleType("_flind_wave104_private_http_urls")
        urls.urlpatterns = [
            path("csrf/", csrf),
            path("login/", sign_in),
            path("me/", whoami),
            path("logout/", sign_out),
        ]
        sys.modules[urls.__name__] = urls

        # The full Flind app swaps AUTH_USER_MODEL away from auth.User. The
        # scoped migration pass therefore correctly omits auth_user: install
        # that framework-only model in this disposable test DB explicitly.
        # This is a scratch auth surface, never a Flind model migration.
        if "auth_user" not in connection.introspection.table_names():
            with connection.schema_editor() as editor:
                editor.create_model(User)

        alice = User.objects.create_user("flind-synthetic-alice", password=secrets.token_urlsafe(24))
        bob_password = secrets.token_urlsafe(24)
        bob = User.objects.create_user("flind-synthetic-bob", password=bob_password)
        # Fresh random password used for Alice; change it once to retain an
        # in-process secret without writing credentials or sensitive receipts.
        alice_password = secrets.token_urlsafe(24)
        alice.set_password(alice_password)
        alice.save(update_fields=["password"])

        client = Client(enforce_csrf_checks=True)
        csrf_response = client.get("/csrf/", secure=True)
        csrf_value = client.cookies["csrftoken"].value
        unauthorized = client.post("/login/", {
            "username": alice.username, "password": alice_password,
        }, HTTP_REFERER="https://testserver/login/", secure=True)
        result["auth_csrf_missing_rejected"] = unauthorized.status_code == 403

        foreign = client.post("/login/", {
            "username": alice.username, "password": alice_password,
        }, HTTP_ORIGIN="https://hostile.example.invalid",
           HTTP_X_CSRFTOKEN=csrf_value, HTTP_REFERER="https://testserver/login/", secure=True)
        result["auth_hostile_origin_rejected"] = foreign.status_code == 403

        incorrect = client.post("/login/", {
            "username": alice.username, "password": "incorrect",
        }, HTTP_X_CSRFTOKEN=csrf_value, HTTP_REFERER="https://testserver/login/", secure=True)
        result["bad_password_rejected"] = incorrect.status_code == 401

        correct = client.post("/login/", {
            "username": alice.username, "password": alice_password,
        }, HTTP_X_CSRFTOKEN=csrf_value, HTTP_REFERER="https://testserver/login/", secure=True)
        result["password_login_http_accepted"] = (
            csrf_response.status_code == 200
            and correct.status_code == 200
            and client.get("/me/", secure=True).json() == {
                "authenticated": True, "user_id": alice.pk,
            }
        )
        alice_sid = client.cookies["sessionid"].value
        result["flind_session_user_id_stamped"] = Session.objects.filter(
            session_key=alice_sid, user_id=alice.pk,
        ).exists()

        independent = Client(enforce_csrf_checks=True)
        result["unrelated_client_stays_anonymous"] = (
            independent.get("/me/", secure=True).json()["authenticated"] is False
        )

        independent.get("/csrf/", secure=True)
        other = independent.post("/login/", {
            "username": bob.username, "password": bob_password,
        }, HTTP_X_CSRFTOKEN=independent.cookies["csrftoken"].value, HTTP_REFERER="https://testserver/login/", secure=True)
        bob_sid = independent.cookies["sessionid"].value
        result["two_user_sessions_separated"] = (
            other.status_code == 200
            and bob_sid != alice_sid
            and independent.get("/me/", secure=True).json()["user_id"] == bob.pk
            and client.get("/me/", secure=True).json()["user_id"] == alice.pk
            and Session.objects.filter(session_key=bob_sid, user_id=bob.pk).exists()
        )
        csrf_fail = client.post("/logout/", HTTP_REFERER="https://testserver/logout/", secure=True)
        result["unsafe_logout_without_csrf_rejected"] = (
            csrf_fail.status_code == 403
            and client.get("/me/", secure=True).json()["user_id"] == alice.pk
        )
        # Django rotates the CSRF token when the user logs in.
        signed_in_csrf = client.cookies["csrftoken"].value
        done = client.post("/logout/", HTTP_X_CSRFTOKEN=signed_in_csrf, HTTP_REFERER="https://testserver/logout/", secure=True)
        stale = Client(enforce_csrf_checks=True)
        stale.cookies["sessionid"] = alice_sid
        result["logout_revokes_http_session"] = (
            done.status_code == 200
            and client.get("/me/", secure=True).json()["authenticated"] is False
            and stale.get("/me/", secure=True).json()["authenticated"] is False
            and not Session.objects.filter(session_key=alice_sid).exists()
        )

        Session.objects.filter(session_key=bob_sid).update(
            expire_date=timezone.now() - timedelta(seconds=3)
        )
        result["expired_session_unreadable_via_http"] = (
            independent.get("/me/", secure=True).json()["authenticated"] is False
        )
        qualified = all(result[k] for k in FLAGS)
        result["framework_http_login_flind_sessionstore_qualified"] = qualified
        if qualified:
            result.pop("blocker")
    except Exception as exc:
        result["blocker"] = "Disposable Django HTTP probe: " + type(exc).__name__
    finally:
        if "django.db" in sys.modules:
            from django.db import connections
            connections.close_all()
    return result


def migrate_then_probe(port: int, password: str, db_name: str) -> dict:
    done = migrate_auth_and_sessions(port, password, db_name)
    if done.get("django_framework_auth_session_qualified") is not True:
        return blocked("Private auth/session migrations unavailable")
    return prove_django_http_login(port, password, db_name)


def qualify_http_login() -> dict:
    if audit_runtime_lock().get("direct_lock_qualified") is not True:
        return blocked("Exact Python direct dependency lock unavailable")
    cluster = isolated_postgres(on_ready=migrate_then_probe)
    child = cluster.get("django_migration_plan") or {}
    result = blocked(child.get("blocker") or "Private PostgreSQL HTTP login unavailable")
    for key in FLAGS:
        result[key] = child.get(key) is True
    qualified = bool(cluster.get("postgres_component_passed") is True
                     and child.get("framework_http_login_flind_sessionstore_qualified") is True
                     and all(result[key] for key in FLAGS))
    result["framework_http_login_flind_sessionstore_qualified"] = qualified
    if qualified:
        result.pop("blocker")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_http_login()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Private real Django HTTP + Flind SessionStore:",
              "PASS" if result["framework_http_login_flind_sessionstore_qualified"] else "BLOCKED")
        print("Production Flind custom user/OAuth/tenant/browser: NOT QUALIFIED")
    return 0 if result["framework_http_login_flind_sessionstore_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
