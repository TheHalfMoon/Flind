# Wave 85 — Synthetic Kafka CLI to ClickHouse relay qualification

## Purpose

Waves 83 and 84 separately qualified **actual native** temporary
ClickHouse and Apache Kafka 4.3.1 components on the authorized Mac.
They did NOT qualify a joint data path. This wave adds a bounded
integration entry point to exercise both real services in the same
temporary run without Docker or paid infrastructure.

**This is not the Flind SDK, HTTP capture endpoint, production Kafka
consumer, materialized view, distributed events schema, dashboard or
release end-to-end test.** The test-only relay is Python.

## Implementation

- The Wave84 Kafka KRaft harness now accepts an optional synthetic
  on_consumed callback. It runs only after Kafka CLI consumers return
  the exact three predefined JSON messages; normal callers retain
  their previous behavior.
- The callback uses the existing localhost-only, memory-bounded,
  temporary ClickHouse harness and verifies canonical event columns
  from the Flind repository's actual source SQL template.
- Replays the **actual messages read from Kafka**, not a new locally
  fabricated batch, to a disposable ClickHouse Memory table.
  Validates exact fixed fixture, order, team identity and safe SQL
  before sending data.
- Queries team-scoped counts, pageviews, distinct IDs and purchases
  with a colliding test distinct ID, and asserts both cross-team
  path checks return zero.
- Unconditionally drops the temporary table after its creation;
  nested server harnesses stop ClickHouse and the Kafka process
  group after failure or completion.
- Exposes a separate synthetic_kafka_cli_to_clickhouse_relay_qualified
  receipt. It does NOT set sdk_ingestion_qualified,
  flind_production_ingester_qualified,
  production_kafka_to_clickhouse_qualified,
  production_events_schema_qualified, dashboard_query_qualified,
  tenant_authorization_qualified or release_qualified.

## Tests and limits, 2026-10-25

**9/9 local Python unit tests PASS** for exact fixture admission,
bounded SQL, malicious or modified message rejection,
team-filtered aggregates, simulated leakage, failed insert cleanup,
untrusted service receipts and refusal to claim release success.
Two additional callback-focused guardrail tests were added to the
existing Kafka Wave84 suite, checking that the callback runs after
an exact readback and never runs for tampered consumed events.

**LIVE JOINT KAFKA + CLICKHOUSE QUALIFICATION: NOT RUN.**
The authorized Mac connection exceeded its Desktop Commander
monthly quota. Do not retry or reconnect that exhausted connector.
Independent real Kafka and real ClickHouse results from Waves 83
and 84 remain valid component evidence, NOT a joint run.

## Reproduction when Mac access is available

With locally verified official Apache Kafka 4.3.1 binaries, native
ClickHouse and at least 10 GiB safe free temporary disk, run the
new Python test module, the existing Wave84 Kafka guards, and then:

python3 tools/flind/qualify_kafka_clickhouse_relay_wave85.py --kafka-home /absolute/path/to/kafka_2.13-4.3.1 --json

The command returns nonzero on failed qualification. A future real
PASS must require receipt from both temporary services, not just
two separately successful component probes.

## Remaining NO-GO gates

Full Django migration graph; actual Flind SDK HTTP capture, Kafka
production topic, native Flind ingestion consumer and materialized
view; production event schema and dashboard readback; tenant and
OAuth authorization; full frontend build, TypeScript and browser E2E.

Keep Issue #82 OPEN; release NO-GO. Repo private, inherited Actions
disabled, no paid services, deployment or publication; preserve
mandatory original source legal LICENSE/NOTICE attribution.
