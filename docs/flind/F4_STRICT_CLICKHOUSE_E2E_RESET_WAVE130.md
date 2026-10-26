# Wave 130 — Fail closed on incomplete isolated ClickHouse E2E resets

## Defect and consequence
`nodejs/tests/helpers/clickhouse.ts::resetTestDatabase()` issued three groups of `TRUNCATE` requests using `Promise.allSettled`, but never inspected their rejected results. Even after `ensureTestDatabase()` checked the selected database name, a missing table, SQL failure or unavailable server could leave stale test data and let the real Rust → Node → Kafka → ClickHouse service suite advance with an invalid fixture.

## Fix
- The three original bounded groups (five/five/three tables) still run; each group now feeds its real `PromiseSettledResult` values into `assertIsolatedClickhouseReset`.
- Only sessions with `FLIND_E2E_DESTRUCTIVE_ACK` set are strict; the dedicated service-E2E runner already validates its exact acknowledgement and disposable loopback-only sandbox before importing Jest.
- When any truncate rejects during that isolated run, fail with a generic phase-specific message. Do not reproduce database error text, since it may contain credentials or paths.
- Other partial-schema Node test suites keep the historical best-effort semantics; no production worker or database schemas were changed.

## Validation performed
A direct Node 22 type-stripping execution of the new pure TypeScript guard exercised three concrete cases: successful reset, tolerated rejection outside the isolated run, and strict rejection without leaking a synthetic secret. All passed. GitHub source-level checks confirmed all three original Promise.allSettled groups are now asserted and the test refers to the new helper. The added standalone `tools/flind/test_clickhouse_reset_fail_closed_wave130.mjs` is intended to execute in a complete checkout with `node --experimental-strip-types`.

**Not yet executed:** full monorepo Jest, real destructive E2E against owned migrated databases, production Node worker start, full Kafka/ClickHouse durability and dashboard readback. Keep issue #82 open, release NO-GO. Repo must remain private, inherited Actions disabled, no publishing, deploying or paid services; preserve legally required attribution.
