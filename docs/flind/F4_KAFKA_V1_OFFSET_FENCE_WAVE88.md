# Wave 88 — Kafka v1: never acknowledge failed background work

## Production defect and scope

The Node.js Kafka v1 consumer previously called
`void backgroundTask.finally(async () => { ... storeOffsetsForMessages(...) })`.
A JavaScript `finally` callback executes after **rejection as well as
fulfillment**. The consumer could therefore store offsets for a batch
whose scheduled side effect failed. Its asynchronous observer could
also produce an unhandled rejected promise.

If a later background task finished before an older failed task, the
consumer also risked acknowledging offsets beyond work that had not
completed successfully. This risks silent loss of events after Kafka
consumer group restart.

Kafka v2 already has its own separate fatal failure/offset fencing
mechanism, so this wave deliberately changes **only Kafka v1** and
does not override the CONSUMER_USE_V2 runtime selection.

## Implementation

- Add `OffsetCommitGate`, a dependency-free FIFO acknowledgement
  barrier. Observe each task's fulfillment/rejection immediately;
  a rejection latches a permanent `failed` state on that consumer.
- Offset store callbacks are executed in **batch arrival order**,
  after their own background task completes successfully. A failed
  batch or offset store callback fences all subsequent acknowledgements.
  A later failed task can conservatively fence earlier pending work:
  retry duplicates are acceptable; losing events is not.
- Replace the unsafe `void backgroundTask.finally` with explicit
  fulfillment/rejection bookkeeping. Keep background duration metrics
  and completion timestamps, and remove settled tasks from the
  bounded in-flight list without creating an observer rejection.
- Reject further event processing as soon as the consumer loop
  observes the latched failure; do not silently keep polling and
  acknowledging later events. Wait for the offset gate when normal
  processing or a clean consumer shutdown drains tasks.
- Preserve Kafka topic, partition, message, handler, offset store
  implementation, and existing configuration behavior.

## Tests executed — October 25, 2026

- **6/6 isolated Node.js tests PASS** against the actual new
  `offset-commit-gate.ts` compiled with TypeScript 5.x:
  out-of-order completion still stores FIFO, failed earlier work
  blocks later acknowledgements, later failure blocks pending older
  work, subsequent healthy tasks remain fenced after rejection,
  thrown offset store callbacks poison the gate, and successful work
  is acknowledged exactly once.
- **Isolated `tsc --strict --noEmit` PASS** for the new gate.
- **7/7 source integration conditions PASS** from the GitHub branch:
  old unconditional `finally` gone, gate used at ack point,
  explicit reject handling, fatal checks and drain guards in place.
- Included **6 Jest tests** for the helper and **3 dependency-free
  Python source guards** under Flind's test directories. They have
  not been run in the full private repository environment this
  turn, because the authorized Mac remote tool reached its monthly
  quota and inherited GitHub Actions must remain disabled.

## Remaining qualification

This correction reduces a potential **at-least-once ingestion
acknowledgement safety bug**, but does **NOT** establish successful
production handling, an actual broker replay test, Kafka v1/v2
parity, or full SDK → Kafka → Rust/Node ingestion → ClickHouse →
dashboard evidence. Nor does it finish Django migrations, the
frontend build, tenant authorization or browser E2E.

Keep release issue #82 OPEN and status NO-GO. TheHalfMoon/Flind
remains private, inherited Actions disabled, no deployment,
publication, paid service, or deletion of required source
LICENSE/NOTICE attribution.
