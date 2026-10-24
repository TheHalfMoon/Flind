# Wave 52 — Exact Python/Django dependency-lock gate

## Actual application startup attempt

With Python 3.14.7 and Django 5.2.18 installed in a temporary virtual
environment, a real python manage.py check --deploy --fail-level WARNING
was attempted without user database migrations or a production server.
Initial boot failed importing Celery due to missing structlog.
Installing a small, isolated set of explicitly pinned Celery/logging
packages allowed boot to advance, but the next import failed at missing
pytz from posthog.utils. No Django apps fully loaded, and no migrations
or Django functional tests passed.

This is a dependency-closure problem, not proof that PostgreSQL, Redis,
ClickHouse, Flind authentication or event APIs are healthy.

## Implementation

- Add tools/flind/qualify_django_lock.py, a read-only manifest audit.
- Compare project runtime dependencies in pyproject.toml to exact
  versions in uv.lock and actually installed Python distributions.
- Evaluate supported platform markers without executing arbitrary
  Python code; reject unknown marker syntax instead of silently
  admitting a package.
- Report missing, mismatched and unlocked distributions separately.
- The audit imports no application modules, installs nothing, uses no
  network, does not open user databases, and cannot mutate the repo.
- Keep django_boot_qualified=false and release_qualified=false
  even when all direct packages are installed. Direct lock parity is
  necessary but not sufficient: transitive lock graph, app boot and E2E
  must be separately proven.

Run the audit using the intended target runtime interpreter:

    python tools/flind/qualify_django_lock.py --json

Exit code 2 means the direct runtime environment does not match the
frozen project lock. A 0 result is NOT a Django startup or release PASS.

## Executed Mac evidence, 24 October 2026

- Python 3.14.7 from isolated uv toolchain: PASS.
- Django 5.2.18 package import: PASS.
- Actual manage.py startup: BLOCKED at missing dependency (pytz after
  earlier missing structlog was addressed).
- 202 direct runtime project requirements, of which 201 are applicable
  to macOS arm64 and one (tbb) is Linux x86_64 only.
- Of those 201 applicable dependencies:
  - 6 distributions present at the exact frozen versions
  - 191 missing
  - 4 installed but drifted from the lock
- Mismatched exploratory environment packages:
  python-dateutil, sqlparse, click and asgiref.
- Focused lock-audit tests: 9/9 PASS.
- Full Flind Python source regressions: 389/389 PASS.
- No DB migrations, background consumers, SDK event ingestion or
  application-layer E2E is qualified.

These counts describe only the isolated test environment under
/tmp/flind-runtime-3147, not a production instance or system Python.

## Next runtime admission

Use a separately authorized no-cost runner or sufficiently resourced
isolated environment to install the complete frozen, supported Python
dependency graph. Verify disk and memory budgets before downloading.
Never overwrite machine-wide Python/uv, delete unrelated caches, or
modify shared Postgres schemas. Run exact-lock admission, then a clean
Django app startup, test-only DB migration and application-layer
SDK/ClickHouse readback with negative tenant-isolation tests.
See issue #82.

Keep repo private, inherited Actions disabled, third-party notices
intact; no public deployment, release or paid providers.
