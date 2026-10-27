# Flind Wave 196 — preserve ordering evidence for Kafka empty keys

## Production defect reproduced and fixed (27 October 2026)

The original `FeedOrderSentinel.check()` in
`nodejs/src/ingestion/api/feed-order-sentinel.ts` skipped every Kafka
message where `!message.key` was true. However, Kafka distinguishes a
**null key** (no routing key) from an **empty UTF-8 key** (a real,
zero-length keyed value). Flind's original gRPC converter preserves the
empty key as `''`; its original Node deserializer preserves the
corresponding zero-length Buffer.

Consequently, repeated or regressing Kafka offsets for a real empty
key were previously omitted from the per-routing-key order sentinel,
with no tracked entry, out-of-order count or replay count.

The product now skips **only** `message.key === null`.
Empty strings remain valid keyed identities. The existing
`JSON.stringify([topic,partition,key])` encoding differentiates them
from nonempty strings and keeps topic-partition boundaries intact.

### Red/green evidence from original product source

Command:

```bash
node --disable-warning=ExperimentalWarning --test \
  tools/flind/test_feed_order_empty_kafka_key_wave196.mjs \
  tools/flind/test_joined_ingestion_group_key_wave195.mjs \
  tools/flind/test_production_grpc_driver_wave192.mjs
```

The new test uses **actual product TypeScript**, bundling the original
`FeedOrderSentinel` and `grpcMessageToSerialized` functions with
already-installed esbuild; it mocks only metrics/logging. It never
installs dependencies or opens network sockets.

**Before repair:** 2/7 original Wave196 cases passed (5 failed:
empty-key identity, replay, routing distinction, partition isolation
and consumer-incarnation behavior).

**After repair:** Wave196 **8/8 pass**, Wave195 **7/7 pass**, Wave192
**8/8 pass** = **23/23 pass**. New tests include a production gRPC
converter handoff, replay distinction, null-vs-empty semantics, key
partition/topic isolation, consumer incarnation handoff, and bounded
LRU eviction. `git diff --check` passed.

### Exact scope

This is a real original-source correctness fix for **diagnostic
per-key feed ordering**; it is not proof of delivered event order or
end-to-end Kafka exactly-once correctness. Kafka broker replay,
consumer restart, actual production joined pipeline, durable production
ClickHouse views, authenticated Django API and SDK/browser flows remain
unqualified.

Private repository; do not deploy/publish or incur paid services.
The release remains NO-GO until independent full-stack and branding
gates are met.
