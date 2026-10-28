# Flind Wave 214 - Original native Jest, Kafka key parity and sandbox identity

## Source-backed issues discovered

1. The original shared Jest setup in `nodejs/jest.setup-env.ts`
   overwrote `CLICKHOUSE_DATABASE` with an ordinary shared test database.
   That conflicts with the unique `flind_test_<12+ chars>` database explicitly
   selected and checked by the isolated Rust/Node service E2E runner.
   A full native service run would fail its own `beforeAll` admission check.
2. The original `FeedOrderSentinel` Jest suite treated an empty string Kafka
   key as unkeyed, unlike the production TypeScript and Rust code.
   Kafka `null` means no key; an empty string is still a real zero-byte key.
   The stale expectation failed under genuine Jest.

## Corrections

- `selectTestClickhouseDatabase` preserves the **fully admitted** unique
  sandbox database. Any partial, spoofed or mismatched `FLIND_E2E_*`
  environment now aborts the shared Jest setup before DB modules are imported.
  Ordinary non-service Jest suites retain their previous test database.
- Clarify the original Jest test: a null Kafka key is skipped but an empty
  Kafka key is tracked and its offset regression is counted. The first-party
  production sentinels are unchanged; no weakened ordering policy.
- No production data, shared databases, destructive E2E, paid services,
  deployment or public release.

## Actual qualification on Windows/WSL Node 24.15.0

- Restored tracked workspace sources and exact missing patch file from Git.
- `pnpm@11.28.5` verified the **4,010-entry** lockfile against its
  supply-chain policies, then installed **2,164** packages under WSL with
  `--frozen-lockfile --ignore-scripts`. WSL store is isolated on Linux volume.
- Native first-party Jest `batch-budget.test.ts`: **4/4 PASS**.
- Native first-party Jest `grpc-server.test.ts` plus
  `feed-order-sentinel.test.ts`: **48/48 PASS** after correcting stale test.
  Prior native attempt: **47/48 PASS**, proving the actual mismatch.
- Independent Node 24 `node:test` sandbox identity regression: **5/5 PASS**,
  including tampered ClickHouse, missing acknowledgement, partial environment.
- Source-only ingestion boundary check: **PASS**, zero new violations.
- Additional native Jest (grpc/kafka converters and batch metrics): **21/21 PASS**. Total six native first-party Jest suites: **73/73 PASS**.
- Targeted pin-locked native node-rdkafka/re2 rebuild: exit 0; both add-ons plus tsx load under Node24. Original service native preflight: PASS.

## Limitations

The native node-rdkafka and re2 add-ons were successfully built from lockfile-pinned sources after the safe dependency install, and first-party service preflight passes. This does NOT qualify Kafka -> Rust -> production Node joined analytics -> durable ClickHouse. Isolated PostgreSQL/Redis/ClickHouse services, migrations and actual original destructive service Jest E2E were not run or qualified.

**Release NO-GO**. Repo PRIVATE; GitHub Actions disabled. This wave does
not authorize publishing, deploying or modifying production data.
