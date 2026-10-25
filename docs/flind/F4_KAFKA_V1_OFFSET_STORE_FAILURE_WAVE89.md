# Wave 89 — Fail closed on Kafka v1 offset-store errors

## Verified defect in the real ingestion consumer

Wave 88 introduced `OffsetCommitGate` to prevent Kafka v1
acknowledgements when background event processing fails. However, the
consumer's existing `storeOffsetsForMessages` implementation still
**caught `rdKafkaConsumer.offsetsStore` errors without rethrowing**.
As a result, the gate's callback appeared successful, and later
batches could attempt to advance offsets past a batch whose Kafka
offset was not accepted.

This is an **at-least-once delivery safety** defect. The correct
conservative outcome is to halt subsequent acknowledgements and let
the consumer replay uncommitted work, even if an offset-store failure
occurred during rebalancing. Duplicate processing is preferable to
silently skipping an event.

## Change

The actual `nodejs/src/common/kafka/consumer/consumer-v1.ts`
`storeOffsetsForMessages` catch block now **rethrows the exact
original error** after its existing log and exception capture.
Because the method is invoked from the Wave88
`offsetCommitGate.observe` callback, the gate latches the storage
failure and refuses to acknowledge subsequent batches. The
consumer loop's existing Wave88 failure checks then prevent further
processing. No changes were made to the Kafka v2 consumer, SDK,
topics, serialized event schema, producer or database.

## Verification in this session (October 25, 2026)

- **6/6 Node.js tests PASS** on an isolated TypeScript component
  reproducing the exact changed offset-store catch behavior and
  integrating the Wave88 offset gate. The tests covered healthy
  storage, empty batch, preserving the original store error,
  preserving it if assignment inspection also fails, poisoning the
  gate after store failure, and permitting sequential healthy stores.
- **Isolated strict `tsc` compilation PASS** for the test subset.
- Added **3 actual repository Jest tests** to the existing
  `consumer-v1.test.ts` mock Kafka suite (error identity, poison
  gate and refusal of later offset stores, healthy offsets).
- Added **3 Python source contract regression tests** requiring
  rethrow after diagnostics and gate integration.

**Not run:** the full project Jest tests or an actual Kafka broker
rebalancing/replay scenario. Remote Desktop Commander for the
authorized Mac hit its monthly quota and inherited GitHub Actions
remain intentionally disabled. The isolated subset is not a
substitute for live ingestion evidence.

## Open release gates

Actual production SDK capture → Kafka → Rust/Node worker →
ClickHouse → dashboard readback remains **NOT QUALIFIED**.
Complete Django migrations, frontend production build and TypeScript,
browser E2E, OAuth and tenant isolation also remain open.

Keep Issue #82 open and release status **NO-GO**. Repository stays
private, no deployment/publication or paid service. Preserve
mandatory source LICENSE/NOTICE attribution.
