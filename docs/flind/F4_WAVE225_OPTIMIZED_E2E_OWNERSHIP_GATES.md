# Wave 225 — prevent Python -O from bypassing Flind service ownership checks

## First-party finding

The original `tools/flind/e2e/verify_wave216.py` uses fifteen Python `assert`
statements for Docker Compose ownership, service identity, healthy state,
loopback-only host ports, synthetic PostgreSQL database names, Redis `PONG`,
ClickHouse database identity, synthetic ClickHouse row isolation, and command-line
arguments. Under `python -O`, Python compiles `assert` statements away entirely.
Especially importantly, the `SELECT count()` queries embedded within `assert`
expressions never run in optimized mode. A passing output could therefore
misrepresent an unverified or foreign service as Flind-owned.

## Remediation

Replace only these fifteen expressions in the original Wave216 readiness
qualifier with an explicit `require(condition, message)` function raising
`AssertionError` on failed admission. Keeping the existing exception type
preserves the source-backed Wave216 schema-preflight unit-test contract, while
making all checks and SQL readbacks run whether or not Python optimizations
are enabled. The optional ClickHouse synthetic write probe still cleans up
its own temporary table in `finally`. No database names, credentials, service
ports, Docker Compose labels, or first-party operational commands were changed.

## Actual isolated regression

- Source baseline: private main `a5585565391734d7948f7e3a6b816e35eca7db09`.
- Exact original Git blob of `verify_wave216.py`:
  `a096fe44848b1067e035cb66d741836e9d76ba0c`.
- Patched source Git blob: `45e8814ea80de52870a148311453bea975a1781a`.
- New first-party test file Git blob: `1c102b1c24c53db0e87555a21edac5e79ce0828e`.
- Python 3.13.5 optimized execution on the exact **unmodified original** file:
  **16 assertion failures and 1 error** across 13 tests (expected reproduction).
  The original skipped the relevant guards and omitted SQL readback queries.
- Python 3.13.5 ordinary execution on the patched source: **13/13 PASS**.
- Python 3.13.5 `-O` execution on the patched source: **13/13 PASS**.
- `py_compile`: **PASS** for both patched source and new test module;
  both files have maximum source line widths below 120 characters.
- The new tests verify correct owned-service acceptance, foreign project/service
  rejection, unhealthy services, non-loopback and mismatched ports, missing
  synthetic PG databases, wrong Redis/ClickHouse responses, all three
  ClickHouse synthetic row-count checks (including query execution under `-O`),
  temporary-table cleanup, unknown CLI arguments, and no compiler-strippable
  assertions left in the first-party qualifier.

These tests use fake Docker subprocess results and mocked ClickHouse/Redis
responses. **No real Docker, PostgreSQL, Redis, ClickHouse, Kafka, or customer
service was started or contacted.** This is a genuine source-level security
regression, not a native service E2E, schema-migration or release pass.

## Outstanding qualification

The source-only ClickHouse migration inventory PR #259 and PostgreSQL strict
Unix-only server gate PR #258 remain separate drafts pending their original
checkout/native environment gates. Full first-party PostgreSQL and ClickHouse
migrations, original Kafka -> Rust -> Node -> ClickHouse Jest (prior Wave216 4/4
failures), authentication, cross-tenant access, SDK and browser tests are not
qualified. Flind remains PRIVATE; GitHub Actions disabled; no publishing,
releasing, deploying, paid compute, or mutations to unrelated project data.
