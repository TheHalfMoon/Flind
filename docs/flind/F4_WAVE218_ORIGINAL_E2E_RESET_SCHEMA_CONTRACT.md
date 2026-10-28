# Wave 218 - source-bound original E2E schema admission

## Why the previous gate was insufficient

Wave 216 brought up real Kafka 4.3.1 and ran the original Rust/Node
Jest suite, but all four service cases failed because the isolated
PostgreSQL and ClickHouse databases had no original schemas.
Its preliminary readiness check covered four PostgreSQL and four
ClickHouse tables, fewer than the actual first-party reset helpers.

## New fail-closed, source-verified gate

The original destructive reset table names are now verified against:

- nodejs/tests/helpers/sql.ts (POSTGRES_DELETE_COMMON_TABLES_QUERY):
  8 tables in isolated test_posthog.
- nodejs/tests/helpers/sql.ts (POSTGRES_DELETE_PERSONS_TABLES_QUERY):
  10 tables in isolated test_persons.
- nodejs/tests/helpers/clickhouse.ts (resetTestDatabase):
  13 tables in uniquely named test ClickHouse database.

Adding, removing or renaming any first-party reset target requires
review; source drift refuses E2E before contacting a database.

The gate independently requires a nonempty Django migrations ledger
in test_posthog and at least one ClickHouse Kafka-engine table.
It retains strict Docker Compose ownership of flindwave216,
loopback-only private port mappings, authentication and health checks.
Only the two allowlisted disposable PostgreSQL database names may be
queried. Nothing queries Zyara's database or user data.

## Executed qualification evidence, October 28 2026

- A new marked isolated checkout was retrieved at exact private Flind
  main commit a268566e9a63da4955ba34dd18a70b49653536dd.
- Original-source contract and failure-path tests under Python 3.14.7:
  12 of 12 PASS (4 existing Wave216 plus 8 Wave218 regressions).
- Python compilation and Git whitespace validation: PASS.
- No production migrations, API/browser test, publishing or deployment
  were attempted.
- Windows host C disk had ~0.1 GiB free, D had ~10.6 GiB, and WSL
  system commands returned I/O errors. A full reinstall is unsafe
  until both host disk and WSL health are restored.

## Release boundary

Satisfying this prerequisite does NOT prove that the full migration
graph was applied, any Rust/Node joined ingestion worked, durable
events were verified, or tenant isolation passed. The original
PostgreSQL and ClickHouse migrations and first-party service Jest
remain outstanding, as do independent Django auth, SDK and browser
E2E. Release NO-GO. Keep repo PRIVATE and GitHub Actions disabled;
do not publish, deploy, incur paid services or alter other projects.
