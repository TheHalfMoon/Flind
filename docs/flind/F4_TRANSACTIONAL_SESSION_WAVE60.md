# Wave 60 — Transactional readback of custom Django sessions

## Why this matters

Wave 59 proved real Django auth/contenttypes and Flind's
`posthog_session` migrations on a disposable PostgreSQL server.
It did **not** exercise the resulting session table. Wave 60 proves the
table accepts a known synthetic session record, its update, its deletion,
and zero residue after an explicit transaction rollback.

## Safety boundaries

- Execute **only** after Wave 59's scoped framework migrations succeed.
- Start one throwaway SCRAM-authenticated PostgreSQL 17 instance on a
  random loopback-only port; never address the user's local shared DB.
- Require the exact installed Python/Django lock before allocating a
  cluster. Migration subprocesses have 155s caps and the 2.5 GiB disk
  guard from Wave 55.
- Generate a one-off random synthetic session key; no real user IDs,
  credentials, cookies or external data enter the test.
- Inside a single PostgreSQL transaction: INSERT; SELECT expected 1;
  UPDATE; SELECT expected 1; DELETE; SELECT expected 0; ROLLBACK; then
  SELECT expected 0. The receipt is admitted only if all four counts
  are exactly `[1, 1, 0, 0]`.
- Reject psql timeouts, any SQL nonzero exit, missing migrations and
  differing receipts. Output contains booleans only, never SQL logs or
  connection secrets. The database and processes are removed afterward.
- This is a **storage-level** regression, not a Django request/session
  cookie flow, login, OAuth, tenant isolation, full Flind migrations or
  product release. The latter remain `false`.

## Run in a full Flind working checkout

```bash
/tmp/flind-wave53-runtime/bin/python -m tools.flind.qualify_session_crud_wave60 --json
python3 -m unittest tools.flind.test_session_crud_wave60 -q
```

The interpreter path above names the exact-lock-qualified disposable
Mac environment used during local qualification, not a distribution
requirement. Do not install dependencies globally or enable inherited
GitHub Actions. No publishing, deployment, paid services or persisted
test data are needed.

## Gates still open

Finish the full Django migration graph, qualify the custom user model
and real session store under login/logout/expiry, OAuth PKCE, tenant
isolation, Redis/Celery/Kafka jobs, SDK capture to ClickHouse query,
browser and desktop E2E and source identity/security gates. Keep issue
#82 open. Preserve legally required source attribution.

## Executed local evidence — October 25, 2026

- Framework migrations on the same disposable PostgreSQL 17 database: PASS.
  This builds on the verified Wave 59 `auth` and `posthog_session` scopes.
- Synthetic session INSERT / readback: **PASS**.
- UPDATE / readback: **PASS**.
- DELETE / readback: **PASS**.
- Explicit ROLLBACK with zero remaining rows: **PASS**.
- The live result reports `session_crud_qualified=true` and all four
  readback flags true; `custom_user_auth_qualified=false`,
  `full_schema_qualified=false`, `release_qualified=false`.
- Dedicated Wave 60 and related migration tests: **26/26 PASS**.
- PostgreSQL teardown completed; available Mac disk returned to ~4.7 GiB.
