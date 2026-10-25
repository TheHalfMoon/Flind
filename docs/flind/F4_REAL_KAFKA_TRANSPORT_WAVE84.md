# Wave 84 — Real private Kafka KRaft publish/consume

## Actual runtime qualification, 2026-10-25

The authorized Mac has Java 25 but no local Kafka executable and no
available Docker daemon. A standalone Apache Kafka **4.3.1** binary
distribution was downloaded into an ephemeral working directory from
Apache's official distribution host, and its SHA-512 digest was
verified against the accompanying Apache `.sha512` file. The Kafka
archive and executable binaries **are not committed or redistributed**
in Flind's GitHub repository.

The executable `qualify_ephemeral_kafka_wave84.py` runs a bounded,
isolated **single-node KRaft broker/controller** with:

- Only `127.0.0.1` broker and controller listeners, each allocated a
  free local port; only loopback listeners are advertised.
- A private temporary KRaft metadata/log directory, local log output,
  auto-topic creation disabled, single-partition synthetic topic,
  replication factor 1; never a production topic or connection.
- Java/Kafka environment restricted to PATH, isolated HOME/TMPDIR,
  fixed Java headless flags and a heap of **256–512 MiB**.
  Environment tokens, arbitrary KAFKA_* overrides and production
  credentials are not inherited.
- Exact Kafka tool version verified as **4.3.1** before formatting.
  Requires at least **10 GiB** free temporary disk.
- 55-second broker readiness bound; explicit producer, consumer and
  format timeouts; process-group termination on failure or success;
  temporary directory and Kafka topic destroyed on exit.

The broker is tested using actual Apache Kafka CLI producer and
consumer executables and a real local topic, not a broker mock.
The harness publishes three synthetic JSON analytics events from two
fictional team IDs (101 and 202) with intentionally colliding
`distinct_id` values, consumes three messages, validates exact
JSON payload equality and count, and stops the broker. Actual observed
receipt:

```json
{
  "isolated_kafka_passed": true,
  "kafka_version": "4.3.1",
  "synthetic_events_published": 3,
  "synthetic_events_consumed": 3,
  "exact_json_message_roundtrip": true,
  "two_teams_with_colliding_distinct_ids": true,
  "temporary_kafka_storage": true,
  "sdk_ingestion_qualified": false,
  "kafka_to_clickhouse_qualified": false,
  "dashboard_query_qualified": false,
  "release_qualified": false
}
```

No application/SDK capture event or live tenant data was used;
this is **real Kafka transport component evidence** only. It does not
yet prove that Flind's production ingester consumes these messages,
enforces a tenant authorization boundary, or moves records into
ClickHouse. Wave 83 separately qualifies a synthetic real ClickHouse
event-column INSERT/SELECT; combining them through the actual Flind
production worker is still a release blocker.

## Automated unit guards

- **10/10** pure Python Kafka tests PASS: actual known payloads, safe
  loopback config, fake/missing binaries, insufficient disk, invalid
  ports, private environment restrictions, full producer/consumer
  invocation and cleanup, incorrect consumed data, failed topic
  creation and failure cleanup.
- **Real Kafka 4.3.1 end-to-end *transport* test PASS twice** with the
  fully implemented script, including after environment hardening and
  version verification.
- Existing Wave 83 ClickHouse component test and its unit suite remain
  separate and continue to reject promotion to SDK/dashboard/E2E
  qualified.

## How to reproduce (without paid cloud)

Obtain Apache Kafka **4.3.1** binary distribution from
`https://kafka.apache.org/downloads/`, and verify its SHA-512 checksum
against the vendor-provided digest before extracting locally. Do not
commit the binary tarball or install a daemon.

```sh
python3 -m unittest tools.flind.test_ephemeral_kafka_wave84 -q
python3 tools/flind/qualify_ephemeral_kafka_wave84.py \
  --kafka-home /absolute/path/to/kafka_2.13-4.3.1 --json
```

Only a local extracted Kafka distribution and Java are required.
No Docker daemon, registry account, paid cloud or public Kafka port
is used.

## Not yet release-qualified

The full Flind SDK/capture endpoint → Kafka → production ingestion
consumer/materialized view → actual ClickHouse event tables →
dashboard readback chain remains **NOT QUALIFIED**.
The full Django migration graph, frontend build and E2E, OAuth and
tenant isolation also remain blockers. Issue #82 stays OPEN and
Flind release is NO-GO.

Repo **TheHalfMoon/Flind remains private**, inherited GitHub Actions
disabled. No deployment, publication or removal of mandatory original
source LICENSE/NOTICE attribution.
