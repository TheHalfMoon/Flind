# Wave 59 — Real isolated Django auth/session schema

## Purpose

Wave 56 qualified Django contenttypes; Wave 57 demonstrated bounded,
resumable full-schema progress without claiming completion. Wave 59 extends
the **framework-only** migration smoke to Django `auth` and Flind `posthog_session`.
Flind uses `AUTH_USER_MODEL = "posthog.User"`, so completing Django's
framework tables is **not** proof of Flind user-account/login behavior.

## Execution and safety

- Reuse the existing SCRAM-authenticated, disposable PostgreSQL 17 cluster,
  bound to a randomly chosen loopback-only port; never connect to the
  machine's existing database instance.
- Require a complete exact Python 3.14.7 Django runtime lock before creating
  any cluster.
- Permit only `contenttypes`, `auth`, and `posthog_session` as explicitly
  allowlisted application migration targets. The default full-graph command
  remains available separately; arbitrary app labels are rejected.
- Run real `manage.py migrate auth --noinput` and
  `manage.py migrate posthog_session --noinput`, each bounded to 155 seconds and
  subject to the existing 2.5 GiB disk free guard and process-group teardown.
- Check committed rows separately for contenttypes (>=2), auth (>=12), and
  posthog_session (>=3); independently query presence of `auth_group`,
  `auth_permission`, and `django_session`.
- A timed-out migration or missing table is a failure even when other
  migrations committed. SQL output never includes passwords. The private
  cluster and its contents are destroyed at the end.
- `custom_user_auth_qualified=false`, `full_schema_qualified=false`,
  `release_qualified=false` are invariant, even on framework success.

## Reproduction on the authorized Mac

Run from the Flind repository root with the exact-lock-qualified interpreter:

```bash
/tmp/flind-wave53-runtime/bin/python -m tools.flind.qualify_auth_session_wave59 --json
python3 -m unittest tools.flind.test_auth_session_wave59 -v
python3 -m unittest discover -s tools/flind -p 'test_*.py' -q
```

The dedicated environment is local and ephemeral; do not assume that
`/tmp/flind-runtime-3147` (a different minimal interpreter) has the full
dependency lock. Never install dependencies globally or enable deployment.

## Unresolved release blockers

A framework migration pass does **not** verify Flind's custom user model,
authentication and OAuth, organization/tenant isolation, complete Django
schema, background workers/Kafka, SDK capture and ClickHouse query,
frontend assets, CSP/CSRF/HSTS, or actual browser/device E2E. Keep #82
and other open release blockers in place. Keep the repository private,
inherited GitHub Actions disabled, and retain legally required attribution.

## Executed Mac evidence — October 25, 2026

Using the exact-lock-qualified `/tmp/flind-wave53-runtime/bin/python`
and a full source checkout for `manage.py`, the probe returned:

- Isolated PostgreSQL 17 component: **PASS**.
- Real `migrate auth --noinput`: **PASS**, auth 12 and contenttypes 2
  committed migration records.
- Real `migrate posthog_session --noinput`: **PASS**, 3 committed
  session-app migrations.
- Independent PostgreSQL readback: `auth_group`, `auth_permission`,
  and `django_session` all present.
- `django_framework_auth_session_qualified=true`;
  `custom_user_auth_qualified=false`, `full_schema_qualified=false`,
  `release_qualified=false`.
- Test cluster was terminated and removed. No other databases modified.
- A preliminary attempt at Django's conventional `sessions` app
  failed because it is intentionally **not installed**. Flind instead
  installs `posthog.session` with app label `posthog_session`, which
  is the actual qualified target.
