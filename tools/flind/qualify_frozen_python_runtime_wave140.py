#!/usr/bin/env python3
"""Read-only qualification of the *exact locked Python runtime*, not app E2E.

Run inside the target Python interpreter, from the Flind repository root:
    python -m tools.flind.qualify_frozen_python_runtime_wave140 --json

This performs no installs, database writes, network calls, or app imports beyond
the Django version check. Application registry, migrations, SDK, API, tenant
isolation, dashboard and release remain independently unqualified.
"""
from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import subprocess
import tomllib

from tools.flind.qualify_backend_runtime import pinned_python_version, django_import
from tools.flind.qualify_django_lock import audit_runtime_lock

ROOT = Path(__file__).resolve().parents[2]


def source_is_full_checkout(root: Path = ROOT) -> bool:
    """Conservatively reject sparse/unknown checkouts for later app boot tests."""
    try:
        p = subprocess.run(
            ["git", "-C", str(root), "config", "--bool", "core.sparseCheckout"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return p.returncode == 1 or (p.returncode == 0 and p.stdout.strip() == "false")
    except (OSError, subprocess.TimeoutExpired):
        return False


def qualify() -> dict:
    # Always check actual pinned interpreter and installed module first.
    py = pinned_python_version()
    django = django_import()
    try:
        lock = audit_runtime_lock()
        # The checked-in lock must itself contain Django at the installed version.
        with (ROOT / "uv.lock").open("rb") as f:
            packages = tomllib.load(f)["package"]
        locked_django = next(p["version"] for p in packages if p.get("name") == "django")
        installed_django = metadata.version("django") if django.ready else None
        django_pin = installed_django == locked_django
        counts = {
            key: int(lock[key])
            for key in (
                "applicable_direct_dependencies", "installed_locked_direct_dependencies",
                "missing_count", "version_mismatch_count", "unlocked_count",
                "unverified_marker_count",
            )
        }
        if any(value < 0 for value in counts.values()):
            raise ValueError("Invalid lock counts")
        lock_ready = lock["direct_lock_qualified"] is True
    except (OSError, StopIteration, KeyError, TypeError, ValueError, SyntaxError):
        counts = {}
        django_pin = False
        lock_ready = False
    except metadata.PackageNotFoundError:
        counts = {}
        django_pin = False
        lock_ready = False

    matched = bool(py.ready and django.ready and django_pin and lock_ready)
    return {
        "phase": "exact-frozen-python-runtime",
        "python_exact_pin_passed": bool(py.ready),
        "django_import_passed": bool(django.ready),
        "django_exact_lock_version_passed": bool(django_pin),
        "direct_dependency_lock_passed": bool(lock_ready),
        "direct_dependency_counts": counts,
        "locked_python_runtime_qualified": matched,
        "full_source_checkout_available": source_is_full_checkout(),
        "django_app_registry_qualified": False,
        "django_migrations_qualified": False,
        "real_ingestion_and_dashboard_qualified": False,
        "tenant_isolation_qualified": False,
        "release_qualified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind exact locked Python runtime:",
              "PASS" if result["locked_python_runtime_qualified"] else "BLOCKED")
        print("Django app startup, database migrations, release: NOT QUALIFIED")
    return 0 if result["locked_python_runtime_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
