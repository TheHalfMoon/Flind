# Wave 90 — Kafka v1 shutdown remains safe after background failure

## Root cause in production ingestion worker

The actual Node.js Kafka v1 consumer's public `disconnect()` method
previously called:

`await Promise.all(this.backgroundTask.map((t) => t.promise))`

**before** draining its Wave88 offset fence, waiting for the consumer
loop, or calling the native Kafka client's disconnect. If any task
rejected, `Promise.all` rejected immediately and the method exited.
This skipped explicit cleanup and risked leaving a partially connected
broker client or unsettled background tasks.

Waves 88 and 89 correctly fence acknowledgements after background or
offset-store failure, but an operational shutdown must still clean
up, not just report failure.

## Fix applied to consumer-v1.ts

- Set `isStopping` before waiting to prevent new Kafka polling.
- Use `Promise.allSettled` to wait for **every** pending background
  task and collect its rejection cause, even if another task failed.
- Drain the ordered offset commit gate and propagate a synthetic
  shutdown failure if the gate was poisoned without an outstanding
  rejected task. Keep original failed task reasons intact.
- Preserve existing consumer-loop exception logging and wait for it
  before attempting native broker disconnect.
- **Always attempt** native `disconnectConsumer()` after draining.
  If the disconnect fails, keep that failure too.
- After the cleanup attempt, rethrow the single original cause
  unchanged, or an `AggregateError` with all task and teardown
  causes. A clean shutdown remains successful.
- Kafka v2, delivery logic, topic names, offsets, SDK and schema
  remain unchanged.

## Evidence obtained 2026-10-25

- **8/8 real isolated Node 22 tests PASS** running the faithfully
  reconstructed revised `disconnect()` method in a TypeScript class
  with controllable mock broker/consumer-loop/gate resources.
  Scenarios: clean shutdown exactly once, background failure still
  disconnects and preserves original error, waiting for all tasks
  after an early failure, poisoned offset gate still disconnects,
  gate drain and broker cleanup dual error retention, background
  and broker disconnect dual error retention, consumer-loop failure
  logging without skipping cleanup, and draining the gate after
  background completion.
- **`tsc --strict --noEmit` PASS** on that isolated class.
- Added **5 repository Jest regressions** using the existing mocked
  `consumer-v1.test.ts` test harness, and **3 Python source-guard
  checks** for the shutdown safety boundary.
- The full private-repository Jest suite and native broker
  integration were **NOT run**, as the previously connected Mac
  reached its Desktop Commander monthly access quota. GitHub Actions
  remain intentionally disabled. This is **not** a full
  system-level release qualification.

## Remaining hard blockers

The native product SDK → Kafka → Rust/Node ingestion →
ClickHouse production schema → Flind dashboard path is not yet
fully qualified. Complete Django migrations, production frontend
build/TypeScript, OAuth and tenant access boundaries, browser
E2E and broad public egress/identity inventory also remain open.

Keep Issue #82 OPEN and release status **NO-GO**. The repository stays
private; no publication/deployment, paid infrastructure, real user
datasets or removal of mandatory original source LICENSE/NOTICE
attribution.

To run full mocked consumer tests when the repo's Node dependencies
are available:

`pnpm --filter @flind/nodejs exec jest --runInBand --runTestsByPath src/common/kafka/consumer/consumer-v1.test.ts`

Independent guard:

`python3 -m unittest tools.flind.test_kafka_v1_disconnect_cleanup_wave90 -q`
