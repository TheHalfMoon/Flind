# Wave 94 — Kafka v1 native error and health diagnostic redaction

## Why

Wave 91 stopped serializing Kafka client configuration on four lifecycle callbacks. However, Kafka v1 still logged raw native errors, their messages and stacks, rebalance errors, native `event.log` payloads, and offset-store errors in other paths. Native strings can contain SASL passwords, OAuth bearer tokens, certificates or transport metadata. The health-check assignment error also exposed raw exception messages, and several `captureException` calls forwarded those raw exceptions to the application's telemetry mechanism.

## Implementation

- Add `safeKafkaErrorContext(unknown)` with a strict numeric/boolean allowlist: safe integer `errorCode`/`errno`, boolean `isFatal`/`isRetriable`. Never stringify an error, invoke `toJSON`, or forward arbitrary message/stack/origin/config fields. Hostile getters fail closed.
- Apply the helper to Kafka v1 rebalance, query-watermark, metadata, native event, connect, partition revoke, offset commit/store, background consumer loop and disconnect diagnostic paths.
- Replace the untrusted native `event.log` text with a fixed event marker.
- Redact assignment failure details returned by the consumer health check; preserve a static error classification and safe structured codes.
- Replace five raw native `captureException(error)` payloads with static errors while rethrowing original exceptions unchanged for control-flow and offset safety. The non-native fixed background bookkeeping exception remains as before.
- Update Wave 88 and Wave 91 source guards to reflect equivalent protection after the Wave 93 cleanup delegation and the Wave 94 shared error allowlist. No Kafka wire protocol, offset ordering, consumer group behavior or environment config changes.

## Verification on authorized macbook — October 25, 2026

- 25/25 targeted Python regressions across Waves 88–94 PASS after updates.
- 8/8 dependency-free Node 26 runtime assertions against the actual TypeScript helper PASS, including secret-bearing messages, toString/toJSON traps, hostile getters, invalid numeric fields, strict diagnostic shape and config filtering.
- Isolated TypeScript `tsc --strict --noEmit` PASS using a temporary free npm TypeScript compiler.
- `git diff --check` PASS.

The full `nodejs` Jest test suite, actual native node-rdkafka consumer callbacks, live Kafka error injection and full production SDK → Kafka → ClickHouse → Dashboard E2E were **not qualified** in the sparse checkout. The new Jest regressions are checked into the source but require the full installed workspace to execute.

## Release boundary

Security hardening of logging does not prove tenant isolation, successful Django migrations, Kafka capture/readback, frontend build or browser E2E. Issue #82 remains open and the beta release is **NO-GO** until its real integration gates are met. Private repository; GitHub Actions inherited workflows disabled; no publication/deployment or paid resources; original legal attribution preserved.
