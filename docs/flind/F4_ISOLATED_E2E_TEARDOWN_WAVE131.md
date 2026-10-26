# Wave 131 — Protect real service-E2E teardown after admission rejection

## Defect

Jest executes `afterAll` even when a suite's `beforeAll` failed. The original first-party `rust-ingestion-consumer.serial.test.ts` rejected unsafe/non-isolated endpoints in `configureParentTestEnv()`, but its unconditional `afterAll` still called PostgreSQL `resetTestDatabase()` and ClickHouse `resetTestDatabase()`. Direct or misconfigured Jest invocations therefore had a destructive cleanup path after sandbox refusal.

## Correction

- The real service E2E now sets `sandboxAdmitted` only **after** `configureParentTestEnv()` verifies the complete disposable sandbox.
- `afterAll` delegates to the dependency-free `cleanupAdmittedRustNodeE2E` which returns without touching any database when admission was refused or a ClickHouse client was never created.
- After successful admission, PostgreSQL and ClickHouse cleanup are each attempted independently, and ClickHouse `close()` is attempted even on failed cleanup.
- Failures make the suite fail with a generic count of failed cleanup stages, without leaking connector error messages that may include credentials.
- Normal test event handling and production application code remain unchanged.

## Executed evidence

Fetched the GitHub branch file contents to an isolated temporary source-proof directory on the connected Mac; executed the actual committed pure-TS helper under already installed local Node 24 with `--experimental-strip-types`, plus source-wiring assertions for the real Jest suite. **PASS, exit 0**: rejected setup with/without client performs no cleanup, admitted success runs Postgres → ClickHouse → close; independent Postgres, ClickHouse and close failures each force test failure without skipping later stages; all-stage failure is counted and sanitized. All tests are synthetic fault-injection, not destructive real database tests.

## Still blocked

The full first-party service Jest suite needs an isolated pre-migrated disposable PostgreSQL/ClickHouse/Kafka/Redis environment, supported native `node-rdkafka` dependencies and production Node workers. Neither that suite nor end-to-end Dashboard readback was executed in this wave. Issue #82 stays open, release is **NO-GO**. Repo private, inherited workflows disabled; no deploy, publish, paid services or removal of mandatory legal attribution.
