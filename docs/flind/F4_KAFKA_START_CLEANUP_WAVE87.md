# Wave 87 — Clean up failed Kafka consumer startup before scope publication

## Actual production lifecycle defect

The **live Node.js common ingestion consumer** builds a Kafka consumer and awaits
`connect()` in `KafkaConsumerComponent.start()`. If the connection rejects
after allocating resources, `start()` previously threw **before returning**
the `{ value, stop }` pair to the owning `ScopeRunner`. That runner can
only roll back already-started components. It cannot disconnect a consumer
whose `start()` never returned a stop handle.

The failure could therefore leave resources associated with a partially
connected Kafka consumer until process exit, complicating retries and clean
startup/shutdown of ingestion workers.

## Fix

- Wrap the real Kafka `connect()` in `try/catch`. On rejection or synchronous
  throw, **attempt `disconnect()` exactly once before propagating** the error.
- If `disconnect()` succeeds, rethrow **the original connect error object**.
  If cleanup also fails, throw `AggregateError([connectError, disconnectError])`
  so neither failure is lost or silently ignored.
- The successful path is unchanged: the component returns the same consumer,
  instrumented batch handler, and `stop: () => consumer.disconnect()`.
- No change to Kafka offsets, topic names, event processing, SDK payloads,
  broker addresses or persistence.

## Verification on 2026-10-25

- **7/7 actual isolated Node.js behavior tests PASS** using TypeScript's
  `transpileModule` on the modified component with mocked Kafka factory,
  tracing and consumer interfaces. Cases include successful startup/stop,
  unchanged instrumented handler, asynchronous and synchronous connect
  failures, double-failure `AggregateError`, deferred cleanup on success,
  and propagating a failed normal stop.
- **Isolated TypeScript `tsc --strict --noEmit` PASS** using local minimal
  ambient declarations that match the retrieved consumer interface.
- Added **6 Jest tests** to
  `nodejs/src/ingestion/common/utils/kafka-consumer.test.ts` to repeat
  important startup/cleanup behaviors under the project's actual test setup.
- **Those full repository Jest tests were NOT run**, because authorized
  Mac access hit the Remote Desktop Commander quota and inherited GitHub
  Actions are intentionally disabled. No full repository typecheck, CI pass
  or live broker connection is claimed.

## Remaining production release gates

This is a bounded resource-lifetime fix, **not** proof of real Flind
SDK → Kafka → Rust ingestion → Node worker → ClickHouse → Dashboard flow.
The full Django schema migrations, production frontend bundle, E2E, OAuth
and tenant isolation remain unqualified. Issue #82 stays OPEN; release
stays **NO-GO**.

Repository `TheHalfMoon/Flind` remains private; inherited Actions disabled,
no deployment or publication, no paid providers. Required source
LICENSE/NOTICE attribution preserved.
