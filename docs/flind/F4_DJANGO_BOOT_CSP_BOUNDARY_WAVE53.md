# Wave 53 — Real Django boot, first-party CSP and fail-closed release check

## What changed

Flind previously had unit/source tests and a compatible local service
stack, but the actual Django app could not be started on macbook because
the frozen runtime graph had not been installed.

Using a temporary, monitored and fully isolated Python 3.14.7 environment,
we installed the exact uv.lock production dependency graph:
- Frozen no-dev installation: 449 external packages and 2 local workspace
  packages, without modifying the repository or global Python.
- Admission in the target interpreter: **201/201 applicable direct
  runtime requirements at their exact frozen versions**, no missing,
  mismatched or unlocked direct distributions.
- A disk-safety process stopped the install if free space would fall under
  2.8 GiB. It completed successfully with about 4.9 GiB free.

The first complete Django check uncovered a **real source import bug**:
posthog/csp_middleware.py referenced POSTHOG_JS_CLOUD_HOST and
POSTHOG_JS_CLOUD_TOKEN that were not exported from posthog.constants.
This failure was not due to the Python environment.

## First-party CSP correction

- Remove the broken import and the original provider's implicit JS
  host and project-token CSP exceptions.
- Optional Flind JS CSP exception is now explicit: FLIND_JS_CLOUD_ORIGIN,
  HTTPS only, exactly matching the configured SITE_URL origin; optional
  FLIND_JS_CLOUD_TOKEN is a bounded safe path segment.
- With no configured Flind origin/token, no inherited provider JS
  script, config path, styles, fonts or image exception is generated
  from the missing variables.
- The inherited default CSP-report destination with an original provider
  token is removed. CSP reports are disabled unless the operator
  explicitly configures CSP_REPORT_ENDPOINT.
- This is a targeted fix, **not** a proof that every broad legacy wildcard
  or every other backend integration has been eliminated. Continue the
  outstanding egress trace (issue #3).

## Read-only Django system-check command

Use the pinned fully installed interpreter:

    python tools/flind/qualify_django_boot_wave53.py --json

The command refuses to invoke Django if the direct runtime lock is
incomplete. It uses a new per-process SECRET_KEY, deliberately
unreachable loopback-only PostgreSQL/Redis connection strings, and a
clean environment with no inherited cloud tokens or API credentials.
The readiness-specific FLIND_READINESS_CHECK=1 prevents the CDP and MCP
application-ready hooks from enqueueing synchronization jobs and writing
Redis locks. Ordinary runtime startup is unchanged.

It executes manage.py check --deploy --fail-level WARNING and reports
a blocked result when there are deployment warnings, an error-level
startup log, a timeout, or nonzero command status. It never calls
migrate, creates data, starts a server or claims product/release E2E.

## Actual evidence, October 24, 2026

- Frozen direct dependency lock: **201/201 PASS**.
- Real Django manage.py check with an ephemeral SECRET_KEY and placeholder
  DB/Redis ports reached the system-check phase after the CSP import fix.
- A diagnostic check at ERROR threshold exited 0 but logged Redis
  initialization failures and four warnings. This is NOT clean evidence.
- Strict readiness check at WARNING threshold correctly returned blocked.
  Warnings: security.W003 (CSRF), security.W004 (HSTS),
  security.W019 (frame options), staticfiles.W004 (frontend/dist absent).
  Startup logs also contained error-severity entries.
- Focused source and probe tests include malicious CSP hosts, tokens,
  absent configs, explicit reporting, and isolation of readiness-mode
  startup jobs.
- First-party CSP and Django boot guards: **16/16 PASS**.
- Full Flind Python regression suite: **405/405 PASS**.

## Remaining NO-GO

The four warnings require feature-aware review. Embedded dashboards and
session replay need intentional framing behavior, so blindly setting
X_FRAME_OPTIONS=DENY would break product behavior. HSTS requires
deployment/TLS qualification; CSRF must be traced through actual routes.
Frontend assets have not been built in this isolated checkout.

Real Django migration on an isolated database, runtime Redis/Celery
workers, Kafka/SDK capture, ClickHouse event readback, query API,
authorization and organization isolation, and browser/desktop/mobile E2E
are still not qualified. **Do not deploy or publish** based on a
successful import or a diagnostic management command alone.

Repository private, inherited Actions disabled, mandatory attribution
preserved, no paid services or public release.
