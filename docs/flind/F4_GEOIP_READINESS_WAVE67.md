# Wave 67 — Ignore optional GeoIP initialization during isolated Django checks

## Root cause

Flind's existing read-only `manage.py check --deploy` probe sets
`FLIND_READINESS_CHECK=1` and supplies only dummy loopback DB/Redis
addresses. The `posthog.geoip` module imported during app population
nevertheless instantiated `django.contrib.gis.geoip2.GeoIP2(cache=8)`.
On the authorized Mac no GeoIP data files were installed, so the
module's exception handler recorded a real `[error]` log:
`Path must be a valid database or directory containing databases`.

Missing GeoIP data is a *known optional-resource condition* during the
isolated settings/static checks. It was noisy startup telemetry, not a
Django error in the code being checked. Runtime lookup already supports
`geoip = None` and returns empty properties for absent data.

## Change

Only while `FLIND_READINESS_CHECK=1`, set the module's `geoip` object
to `None` without constructing GeoIP2 or logging any exception.
Normal development/production, including missing-file exceptions and
error capture, retain their pre-existing behavior and `cache=8` mode.

This is **not** a GeoIP data installation or a production API feature
change. No external egress, GeoIP DB download, secret, paid service or
user data is required.

## Executed Mac evidence — October 25, 2026

- 5/5 AST-extracted source regressions: readiness never instantiates
  GeoIP, production still loads with cache=8, missing-production-DB
  error still reports, even a throwing provider is not contacted during
  readiness, readiness env uses local-only loopback placeholders.
- Real exact-lock Python 3.14.7 Django 5.2.18 `manage.py check --deploy
  --fail-level WARNING` executed using the edited Flind source and
  temporary symlinks for unmodified assets from the full checkout.
- Probe reached Django's system-check summary with four remaining codes:
  `security.W003`, `security.W004`, `security.W019`,
  `staticfiles.W004`. No other deployment flags were altered.
- **`ERROR_LEVEL_STARTUP_LOGS=False` and `GEOIP_DATABASE_ERROR=False`**.
  Before this patch the identical isolated check emitted both.
- The check's process exit remains **1 (NOT QUALIFIED)** because the
  four independent deployment warnings are still unresolved.
- Temporary source symlinks used exclusively by the test harness were
  deleted; the worktree's commit contains only this scoped fix.

## Remaining release gates

- W003: Flind deliberately uses its `CsrfOrKeyViewMiddleware`
  subclass (now key-verified in Wave 66); Django's generic security
  checker requires the **literal** name of the default middleware.
  Do not install a conflicting second CSRF middleware simply to hide
  the warning.
- W004: HSTS is a property of a real HTTPS-only deployment. Do not
  force HSTS on the current default `http://localhost:8010` URLs.
- W019: `X_FRAME_OPTIONS=SAMEORIGIN` enables first-party embedded
  application views; CSP frame-ancestors requires real browser checks.
- staticfiles.W004: a complete real Vite frontend build is missing in
  the source checkout. Preserve that warning until the build is proven.

Full Django schema migration, Redis/Celery/Kafka, ClickHouse SDK ingest
and readback, OAuth, tenant isolation, Web/device E2E remain NO-GO.
TheHalfMoon/Flind stays private, inherited GitHub Actions disabled,
no release/publication/deployment/paid cloud, required legal attribution.
