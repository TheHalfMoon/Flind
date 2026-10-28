# Wave 226 — immutable first-party destructive reset source contracts

## Source-backed safety finding

The original `tools/flind/e2e/schema_preflight_wave216.py` admitted the destructive
Node/Jest database-reset preflight by matching only **8 common PostgreSQL, 10 persons
PostgreSQL and 13 ClickHouse table names**. That misses changed statements within
the very same reset bodies (for instance extra SQL on the same line, changed
dynamic `DELETE` expressions or removal of `assertIsolatedClickhouseReset()`
while all 31 named table calls still appear). The original service test resets
are destructive and must fail closed on unreviewed reset-body changes.

## Fix and exact immutable source evidence

Wave226 pins SHA-256 of the **three exact source sections extracted by the already
existing original anchors**:

| Original section | SHA-256 |
| --- | --- |
| `POSTGRES_DELETE_COMMON_TABLES_QUERY` backtick SQL body in `nodejs/tests/helpers/sql.ts` | `52b6a3c5a25dbe8491a0583ab417d61a7bd3473ab0a455c8f3dbf11cd7b7ff00` |
| `POSTGRES_DELETE_PERSONS_TABLES_QUERY` backtick SQL body in `nodejs/tests/helpers/sql.ts` | `f9edca9ee7a288977059cfee04d0ac3dde81bf5fd621f590c60fad8f0f26c299` |
| `resetTestDatabase()` ClickHouse body up to `// Topics that this database` in `nodejs/tests/helpers/clickhouse.ts` | `b17ac8253a508b275513af6edf47ef8b8590525755e1f52b0f8665ce32d6c204` |

The sections are from the actual authenticated **private Flind merged main
`cd89e0995cfefb385a7efc88415d62fc02e9a639`** (original TypeScript
Git blobs `4ae38ad8cb87ce3f6f2ed5a4cec9456fe6826bf3` and
`10e6deab99aac542c9f90415bb02e423ee2dacbb`). Any body change now raises
`ValueError("reset source digest changed (contract changed)")` **before**
calling Docker or any PostgreSQL/ClickHouse query. The existing names-and-count
checks are preserved after SHA-256 verification. The error retains both the
new `reset source digest changed` diagnostic and the legacy `contract changed`
substring required by existing Wave218 safety regression tests. An unrelated comment outside
the reset source sections does not change these section digests.

## Executed verification

- Independently extracted original three source sections from authenticated
  private GitHub main; lengths **1,467 / 1,327 / 1,572** text bytes.
- Recomputed expected SHA-256 both with a standalone JavaScript SHA-256
  implementation (validated against the `SHA256("abc")` test vector) and
  **Python 3.13.5 `hashlib.sha256` on exact copied original source fragments**.
  All three exact hashes match; **4/4 negative mutation checks PASS**:
  extra SQL after common `posthog_team`, dynamic `quote_ident()` removal,
  extra SQL after persons `posthog_person`, and removal of a ClickHouse
  `assertIsolatedClickhouseReset` guard.
- A separate isolated Python3.13.5 excerpt test harness on the exact three
  authenticated first-party source bodies executed **7/7 PASS**, including
  SHA256 baseline/known-answer vector, 8/10 unchanged PostgreSQL table-name
  counts despite added extra SQL, 13 unchanged ClickHouse truncate names
  despite deleted guard, and unrelated outside-body comments accepted. These
  are **excerpt-level regression tests, not the complete first-party module
  or repository test suite**.
- Executed the **actual GitHub-blob-matching original Python modules**
  `test_schema_preflight_wave216.py` (4), `test_reset_contract_wave218.py` (8),
  and `test_reset_digest_wave226.py` (7): **19/19 PASS** on Python 3.13.5.
  The exact Python source/test Git blob IDs were independently verified for
  all four files, including the Wave226 patched implementation and test.
  A second real `python -O` run also passed **19/19** (38 successful test
  executions across both interpreter modes). All four compiled with `py_compile`.
- The isolated runtime used a minimal TypeScript helper fixture assembled
  from the **three byte-exact, SHA-256-verified original destructive reset
  sections** rather than the complete original TypeScript helper files.
  These 19 focused first-party Python tests now passed, but a **full Flind
  checkout-wide test/lint pass and original services E2E are still unexecuted**.
  GitHub Actions remain disabled and Desktop Commander monthly usage is exhausted.

## Boundaries and release

This is **source-integrity admission only**. It does not apply original migrations,
verify actual test DB ownership, qualify a ClickHouse or PostgreSQL schema, run
real Kafka/Rust/Node/Jest ingestion, or certify release readiness. PR #258/#259
remain independent Draft work. The real original Wave216 joined service Jest
remains 4/4 FAIL due missing first-party schema. Flind stays PRIVATE, Actions
disabled, **NO-GO** release, no publication/deployment/paid services and no
unrelated customer or project data access.
