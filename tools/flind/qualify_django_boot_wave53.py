#!/usr/bin/env python3
"""Run Flind Django's real system check in an isolated, non-deploying process.

This is a startup/import admission check, not a migration, database,
ingestion, auth or release test. It passes NO inherited API credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import sys

if __package__:
    from .qualify_django_lock import audit_runtime_lock
else:
    from qualify_django_lock import audit_runtime_lock


ROOT = Path(__file__).resolve().parents[2]


def isolated_boot_environment() -> dict[str, str]:
    """Prevent ambient tokens and use intentionally unreachable loopback databases."""
    return {
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "en_US.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "DJANGO_SETTINGS_MODULE": "posthog.settings",
        "FLIND_READINESS_CHECK": "1",
        "SECRET_KEY": secrets.token_urlsafe(64),
        # A non-existent username/database and non-standard closed ports.
        "DATABASE_URL": (
            "postgres://flind_test:unusable@127.0.0.1:65433/"
            "flind_readiness_nonexistent"
        ),
        "REDIS_URL": "redis://127.0.0.1:65434/0",
    }


def diagnostic(output: str) -> str:
    """Retain a bounded error class only, not untrusted log text or secrets."""
    for line in reversed(output.splitlines()):
        value = line.strip()
        if any(value.startswith(prefix) for prefix in (
            "ImportError:", "ModuleNotFoundError:", "SystemCheckError:",
            "django.core.exceptions.", "RuntimeError:", "ValueError:",
            "AssertionError:", "FileNotFoundError:", "TypeError:",
        )):
            # Never copy arbitrary error body or a path with credentials.
            return value.split(":", 1)[0][:120]
    return "No recognized exception class"


def qualify_django_boot(timeout: int = 125) -> dict:
    lock = audit_runtime_lock()
    result = {
        "phase": "django-system-check",
        "direct_dependency_lock_qualified": lock["direct_lock_qualified"],
        "django_system_check_passed": False,
        "release_qualified": False,
    }
    if not lock["direct_lock_qualified"]:
        result["blocker"] = "Frozen direct dependency lock incomplete"
        return result

    try:
        process = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy",
             "--fail-level", "WARNING"],
            cwd=ROOT,
            env=isolated_boot_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = process.stdout + process.stderr
        result["deploy_warning_codes"] = sorted(set(re.findall(
            r"\b(?:security|staticfiles)\.W\d{3}\b", output,
        )))
        result["startup_log_errors"] = bool(re.search(
            r"\[(?:error|critical)\s*\]", output, re.IGNORECASE,
        ))
        result["django_system_check_passed"] = bool(
            process.returncode == 0
            and not result["deploy_warning_codes"]
            and not result["startup_log_errors"]
        )
        if not result["django_system_check_passed"]:
            if result["deploy_warning_codes"]:
                result["blocker"] = "Django deploy or staticfiles warnings"
            elif result["startup_log_errors"]:
                result["blocker"] = "Startup emitted error-level logs"
            else:
                result["blocker"] = diagnostic(output)
    except subprocess.TimeoutExpired:
        result["blocker"] = "Django system check timed out"
    except OSError:
        result["blocker"] = "Django system check could not launch"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_django_boot()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind Django system check: " + (
            "PASS" if result["django_system_check_passed"] else "BLOCKED"
        ))
        if result.get("blocker"):
            print("Reason: " + result["blocker"])
        print("Flind release E2E: NOT QUALIFIED")
    return 0 if result["django_system_check_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
