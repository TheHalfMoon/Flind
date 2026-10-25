# Wave 61 — Strict session-to-user attribution

## Product bug corrected

Flind's custom `posthog.session.backend._auth_user_id` previously used
`int(data[SESSION_KEY])`. Python converts `True` to `1` and accepts
negative/zero identifiers, floats such as `1.4` (becomes `1`), and
values beyond PostgreSQL's signed 64-bit `BigIntegerField`.

Consequently a malformed or stale session could be incorrectly linked
to another user's ID, or a session save could fail due to integer overflow.
This is *not* proof of cross-tenant access, but it violates the
session ownership invariant used for account session lists and revocation.

## Implementation

- Accept positive, at-most-64-bit signed user IDs as native integers
  or ASCII decimal strings of at most 20 characters.
- Reject booleans (even though Python treats them as ints), floats,
  non-decimal/Unicode-digit strings, negative values, zero, oversized
  IDs, and very long numeric payloads without invoking `int` on them.
- Continue refusing attribution whenever the `loginas` impersonation
  flag is present, regardless of the flag value.
- Preserve supported Django login user IDs such as `str(user.pk)`,
  including the largest positive PostgreSQL bigint.
- Sync and async session saves share the same helper, so the correction
  applies to both.
- Add focused no-database regression tests and integration tests that
  verify actual persisted rows on create and subsequent save.

## Actual local verification (Mac, October 25, 2026)

- Five standalone source-function tests: PASS, including extreme
  numeric input, impersonation, and boundaries.
- Actual Django 5.2 runtime import with minimal local SQLite settings:
  positive decimal session IDs return correctly; booleans, negative and
  out-of-range IDs are rejected, and impersonation remains unattributed.
- `posthog/session/test/test_backend.py` DB integration tests are
  extended, but they are **not qualified** by this minimal import smoke.
  They must run later against the isolated full Flind backend.

## Follow-up gates

This fixes a concrete attribution defect but does not prove end-to-end
login/OAuth, tenant isolation, full database migrations, SDK->ClickHouse,
frontend or browser E2E. Keep issue #82 OPEN. Do not publish/deploy,
enable inherited Actions or use paid services. Preserve legal attribution.

## Real SessionStore SQLite-memory qualification

Run from the repository root with an isolated Python environment containing
the frozen Django 5.2.18 and `django-loginas==0.3.14` packages:

```sh
python -m tools.flind.qualify_session_user_store_wave61 --json
```

Observed result on the authorized Mac, October 25, 2026:

- `real_django_store_qualified=true`
- An authenticated session saves a positive user ID: PASS.
- A boolean user ID is not attributed: PASS.
- A `loginas` impersonation session is not attributed: PASS.
- Replacing a previously valid ID with a boolean clears its attribution: PASS.
- Existing session display metadata survives save: PASS.
- All data is synthetic; the database exists only in SQLite memory.
- `custom_user_login_qualified=false`, `full_schema_qualified=false`,
  `release_qualified=false`; PostgreSQL integration remains a separate gate.

The probe intentionally suppresses AppConfig.ready signals in its **own**
isolated Django setup, preventing unrelated production startup hooks. This
does not alter production startup. The temporary Python environment used
here is not the full 201-package Flind lock; do not interpret this as
whole-backend readiness.
