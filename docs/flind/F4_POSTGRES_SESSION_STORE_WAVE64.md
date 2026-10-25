# Wave 64 — Qualify the actual Django session store on PostgreSQL

## Why it matters

Wave 59 proved Django framework auth plus Flind's custom session migrations;
Wave 60 proved raw SQL session CRUD and transaction rollback; Wave 61 proved
Django SessionStore behavior using an isolated in-memory SQLite instance.
Those are useful but do not establish whether the **real Django SessionStore**
works with a PostgreSQL-backed custom session model.

This wave uses the authorized, locked Python 3.14.7 runtime with a disposable
SCRAM-authenticated PostgreSQL 17 instance on a random localhost port.
It runs the **real** scoped Django migrations first, verifies their independent
receipts and then exercises the real Flind SessionStore API and ORM.

## Executed session lifecycle

The probe uses only synthetic IDs and local test markers. It verifies:

1. `SessionStore.create()` inserts a session row and stamps a valid
   positive user ID.
2. A **separate** SessionStore instance can decode and read that session.
3. A subsequent session save does not erase middleware-written location
   metadata.
4. Invalid user IDs (e.g. `True`) are never stamped onto the row.
5. Impersonation sessions remain unattributed.
6. Deleting a session row makes it unavailable to future SessionStore loads.
7. Moving its expiry into the past prevents SessionStore loads.

The probe never creates real Flind users, talks to OAuth, contacts any SDK,
triggers provider integrations or accesses a pre-existing PostgreSQL service.
It never returns raw passwords, session keys, test URLs or SQL logs. Test
resources and credentials are destroyed at end of run. No user database is
modified.

## Qualification limits

Even a PASS only means **isolated custom session-storage behavior**, not
a qualified login/logout API, OAuth token/PKCE flow, tenant boundaries,
full Django schema, Kafka/ClickHouse events, browser/desktop experience,
or release. All corresponding gates and issue #82 remain open.

## Reproduction

From a full Flind checkout with the exact locked Python runtime:

```sh
python -m unittest tools.flind.test_postgres_session_store_wave64 -q
python -m tools.flind.qualify_postgres_session_store_wave64 --json
```

The direct Python lock must pass before PostgreSQL is created. If the
migrations or PostgreSQL health do not pass, the session test cannot run.

## Verified evidence

- Unit/guardrail suites for Wave 64 and Waves 59–60:
  **26/26 PASS**.
- Actual PostgreSQL-backed SessionStore runtime qualification is a
  **separate external test** and must be explicitly reported as PASS
  only when the live receipt confirms it.
- Keep the repository private, inherited Actions disabled, no publish
  or deployment, no paid services, and mandatory attribution preserved.

## Real native PostgreSQL evidence — October 25, 2026

Executed against one fresh isolated PostgreSQL 17 cluster using the fully
locked Python 3.14.7 runtime (201/201 applicable direct dependencies).
The real `auth` and `posthog_session` migrations finished successfully
before any synthetic ORM operations began.

The final emitted receipt reported:

| Gate | Result |
|---|---|
| `isolated_postgres_passed` | true |
| `framework_schema_qualified` | true |
| `session_store_postgres_qualified` | true |
| Synthetic authenticated create | true |
| Cross-instance session decode/read | true |
| Preserve middleware-written metadata | true |
| Reject invalid user ID | true |
| Keep impersonation unattributed | true |
| Revoked session unreadable | true |
| Expired session unreadable | true |
| `full_schema_qualified` | false |
| `real_login_qualified` | false |
| `release_qualified` | false |

Actual test exit was successful, with private PostgreSQL teardown complete.
Unit/guardrail suites for Wave 64 plus Wave 59–60: 26/26 PASS.

This is real PostgreSQL-backed ORM evidence, **not** synthetic unit mocks
or evidence that the complete thousands-of-migrations Flind schema passes.
