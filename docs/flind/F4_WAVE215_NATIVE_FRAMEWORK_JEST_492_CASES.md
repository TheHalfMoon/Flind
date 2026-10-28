# Flind Wave 215 - Native original ingestion framework Jest qualification

## Actual executed scope

Windows/WSL, Node.js 24.15.0, pnpm 11.28.5, original source checkout
at the merged Wave214 main. First-party Jest (not a synthetic runner).
Targeted native suite directory: nodejs/src/ingestion/framework.

Command (from nodejs workspace):
  pnpm exec jest --config jest.config.js --runInBand --no-cache --forceExit --testPathPatterns=src/ingestion/framework/

Result: **45/45 suites PASS, 492/492 cases PASS, 0 failures**.
Bounded with a 180-second timeout and 2048 MiB Node heap limit;
actual run finished in about 19 seconds with exit 0.

Covered framework cases for concurrent and sequential chunk pipelines,
batching, branching, fan-out/fan-in, grouping, retries, result handling,
step ordering, event side effects, deadline barriers, cancellation and
documentation examples. Test-generated expected error logs are not
failures. Jest --forceExit was used because the original suite leaves
some handles open; this execution does not assert handle-clean shutdown.

## Provenance and boundaries

All original first-party TS test files and original Jest setup were
executed from the checked-out source with installed frozen-lockfile
dependencies. Wave214 separately qualified six Node API/framework Jest
suites (73/73) and safe ClickHouse sandbox identity tests (5/5).
A passing native framework suite does not imply the full Kafka/Rust ->
production Node joined analytics -> durable ClickHouse E2E has run.

The isolated PostgreSQL, Redis and ClickHouse services, migrations,
Django tenant and auth isolation, SDK/browser E2E and production
persistence remain unqualified. No production data or service was used.

**Release NO-GO.** Private Flind repository; GitHub Actions disabled,
no deployment or publication, no paid tools.
