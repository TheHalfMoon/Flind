# Wave 115 — Preserve Kafka empty payloads and tombstones in the production Node ingestion adapter

## Product correctness fix

The Rust→Node ingestion bridge `nodejs/src/ingestion/api/kafka-message-converter.ts` deserializes `SerializedKafkaMessage` objects emitted by the Rust Kafka consumer HTTP API. Its previous truthiness conversions were:

```ts
const valueBuffer = serialized.value ? Buffer.from(serialized.value, 'utf-8') : null
key: serialized.key ? Buffer.from(serialized.key, 'utf-8') : undefined
```

Kafka distinguishes **a zero-byte value** (valid payload, `Buffer.alloc(0)`) from **a null value** (tombstone). A zero-byte Kafka key is likewise distinct from an absent key. The previous code converted all empty strings into `null` or `undefined`, making an empty payload indistinguishable from a deletion marker at the ingestion boundary. The adapter now tests **explicit null**, preserving zero-byte buffers and the original byte lengths. No changes to Kafka wire format, topics, product schemas, offsets, auth, Redis, ClickHouse or downstream consumers.

The TypeScript-only `Message`, `MessageHeader` and `SerializedKafkaMessage` imports are now correctly declared as `import type`, so running just the actual converter does not cause runtime package imports. Production bundlers also erase these types.

## Repeatable real-function proof — October 26, 2026

Run from the Flind repo on macOS using locally available **Node 26**:

```sh
node --experimental-strip-types --test tools/flind/test_node_kafka_deserializer_wave115.mjs
```

**7/7 PASS, exit 0** against the **actual imported TypeScript function from the production adapter** (not a Python/JavaScript reimplementation or synthetic equivalent). Cases include empty key+empty value+empty header, null tombstone, mixed empty-key/tombstone and null-key/empty-value cases, ordinary JSON key/value, Unicode UTF-8 byte length, and explicit assertion that empty value is not equal to a null tombstone despite both sizes being zero.

Added three matching regression cases to the original `nodejs/src/ingestion/api/kafka-message-converter.test.ts` Jest file; they remain part of the project-native suite once dependency installation is available.

Node's experimental type stripping emits a **non-fatal typeless package warning** because the existing Node workspace is not ESM-designated. The focused suite nonetheless passed. Python and Rust dependencies, Kafka/ClickHouse servers and paid cloud services were not needed. A full product Jest/TypeScript/build check was **not** run: the Node workspace `node_modules` tree is absent and only ~13 GiB disk remained on the Mac. Existing local pnpm package cache (~6.3 GiB) does not itself prove a reproducible complete package installation.

## Project release boundary

This corrects a specific payload-interpretation error in the Rust→Node Kafka adapter. It **does not** establish the running Node.js production ingestion worker, product ClickHouse `events` schema, tenant-scoped API, Dashboard, OAuth/PKCE or frontend/desktop E2E. Wave114's real Rust→Kafka→ClickHouse Kafka Engine / non-durable Memory table test remains valid but distinct from production Node ingestion. Issue #82 remains OPEN and Flind release NO-GO.

No publication/deployment, paid provider, use of real customer data, activation of inherited GitHub Actions, or removal of required donor attribution.
