# Wave 91 — Remove raw Kafka credentials from v1 lifecycle logs

## Root cause in the real ingestion service

The real Kafka v1 consumer merges operational settings from environment
variables such as `KAFKA_CONSUMER_SASL_PASSWORD` into its native
`consumerConfig`. Four lifecycle logs previously included the
**entire native configuration object** or the entire service config:

1. Subscriber ready callback (`subscribed`).
2. Native Kafka connection failure callback.
3. Main consumer-loop failure.
4. Consumer-loop shutdown failure.

Native configuration can include `sasl.password`, `ssl.key.password`,
OAuth bearer configuration and other provider-defined keys. Emitting
it to operational logs risks exposing credentials even though the
consumer needs them to connect.

## Implemented

- New pure, explicitly allowlisted `safeKafkaLogContext` creates
  **only** `{topic, groupId}`; it never spreads, serializes or
  mutates Kafka's real connection configuration.
- Route all four v1 lifecycle log metadata payloads through this
  allowlist. Preserve operational coordinates and diagnostic error
  code, while omitting the raw native Kafka configuration.
- Native `connection.failure` no longer serializes arbitrary error
  and native metrics objects; emit its code plus the safe context.
- Keep the full native config for actual connections, subscriptions,
  topic configuration, environment parsing and SDK compatibility.
  No changes to Kafka offsets, message processing, producer/consumer
  semantics or release configuration.
- Add direct Jest regression tests for subscriptions, connection
  failures and the pure allowlist, plus Python source-contract
  regressions preventing a return to raw credential logging.

## Actual verification, October 25, 2026

- **4/4** direct Node.js pure helper tests PASS using
  `safe-log-context.ts` compiled by the installed TypeScript compiler,
  including native SASL/TLS/OAuth secrets, inherited properties,
  runtime config immutability and strict field allowlisting.
- **`tsc --strict --noEmit` PASS** for the pure helper.
- Source reviewed for four exact lifecycle call sites and confirmed
  each now uses `safeKafkaLogContext(this.config)`. Added four
  repository Python source guard cases to assert this.
- Added two Jest tests using the actual mocked native Kafka callback
  registration from the existing v1 test harness; **the full Jest
  suite was not run** due to the previously exhausted authorized Mac
  remote usage quota. GitHub Actions remain intentionally disabled.

## Explicitly not established

This is a **targeted native Kafka configuration exposure fix**.
It does not comprehensively audit all other telemetry or third-party
Kafka client error payloads. More work is necessary before any
claim of platform-wide egress/logging qualification.

It does not qualify SDK→Kafka→Rust/Node→ClickHouse→dashboard,
full Django migrations, production frontend build, OAuth/tenant
isolation or browser E2E. Release stays **NO-GO**; issue #82
remains open.

TheHalfMoon/Flind stays private, inherited GitHub Actions disabled,
no public deployment, publication or paid services, and mandatory
original-source LICENSE/NOTICE attribution remains untouched.

To reproduce when Node service dependencies are available:

`pnpm --filter @flind/nodejs exec jest --runInBand --runTestsByPath src/common/kafka/consumer/safe-log-context.test.ts src/common/kafka/consumer/consumer-v1.test.ts`

Dependency-free source guard:

`python3 -m unittest tools.flind.test_kafka_v1_log_redaction_wave91 -q`
