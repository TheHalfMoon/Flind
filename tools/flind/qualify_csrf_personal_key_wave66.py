#!/usr/bin/env python3
"""Verify actual Django CSRF rejection and key-based exceptions (no DB/network).

Compiles the production CsrfOrKeyViewMiddleware class unmodified from its
real module and supplies an isolated credential validator. This is Django
behavioral evidence, not a substitute for HTTP auth/DB/E2E verification.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys


def check():
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            SECRET_KEY="flind-isolated-csrf-smoke-not-a-production-secret",
            DEBUG=False,
            ALLOWED_HOSTS=["testserver"],
            INSTALLED_APPS=[],
        )
    import django
    django.setup()
    from django.middleware.csrf import CsrfViewMiddleware
    from django.test import RequestFactory
    from rest_framework.exceptions import AuthenticationFailed

    source = Path(__file__).resolve().parents[2] / "posthog/middleware.py"
    nodes = [
        node for node in ast.parse(source.read_text(encoding="utf-8")).body
        if isinstance(node, ast.ClassDef) and node.name == "CsrfOrKeyViewMiddleware"
    ]
    if len(nodes) != 1:
        return {"django_csrf_qualified": False, "blocker": "Middleware source mismatch"}

    class VerifiedKey:
        current = None
        valid = False

        @classmethod
        def find_key_with_source(cls, request):
            return cls.current

        @classmethod
        def validate_key(cls, candidate):
            if not cls.valid:
                raise AuthenticationFailed("Synthetic key rejected")
            return object()

    namespace = {
        "CsrfViewMiddleware": CsrfViewMiddleware,
        "PersonalAPIKeyAuthentication": VerifiedKey,
        "AuthenticationFailed": AuthenticationFailed,
    }
    unit = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(unit, str(source), "exec"), namespace)
    middleware = namespace["CsrfOrKeyViewMiddleware"](lambda req: None)
    factory = RequestFactory()
    request = lambda: factory.post("/synthetic-write", data={"v": "1"})

    VerifiedKey.current = None
    absent = middleware.process_view(request(), lambda req: None, (), {})
    no_token_rejected = bool(absent and absent.status_code == 403)

    VerifiedKey.current = ("synthetic-fake-token", "query_string")
    VerifiedKey.valid = False
    fake_request = request()
    fake = middleware.process_view(fake_request, lambda req: None, (), {})
    fake_rejected = bool(fake and fake.status_code == 403
                         and not getattr(fake_request, "csrf_processing_done", False))

    VerifiedKey.current = ("synthetic-valid-token", "header")
    VerifiedKey.valid = True
    valid_request = request()
    allowed = middleware.process_view(valid_request, lambda req: None, (), {})
    valid_allowed = bool(allowed is None
                         and getattr(valid_request, "csrf_processing_done", False))

    result = {
        "django_csrf_qualified": no_token_rejected and fake_rejected and valid_allowed,
        "no_token_rejected": no_token_rejected,
        "fake_key_rejected": fake_rejected,
        "valid_key_accepted": valid_allowed,
        "full_auth_qualified": False,
        "release_qualified": False,
    }
    if not result["django_csrf_qualified"]:
        result["blocker"] = "Isolated Django CSRF behavior incomplete"
    return result


if __name__ == "__main__":
    report = check()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["django_csrf_qualified"] else 2)
