# Wave 119 — Real native Rust ingestion-consumer joins isolated Kafka 4.3.1 group

## Qualification goal

Wave117 established first-party Rust ingestion-consumer **build/link**; Wave118 fixed the actual native HTTP readiness false-positive when there is no responsive worker. Wave119 advances the scope to the **real Apache Kafka broker / consumer-group protocol**. This is not a synthetic Kafka CLI-only reader or an emulated consumer.

`tools/flind/qualify_native_consumer_kafka_group_wave119.py` reuses the existing local Kafka 4.3.1 KRaft ephemeral fixture. It starts a real **native Mach-O arm64 Rust ingestion-consumer executable** on `127.0.0.1` with:
- Fresh, isolated one-partition empty `flind-wave119-empty-native-consumer` Kafka topic and `flind-wave119-native-consumer` group, and exact `KAFKA_HOSTS`, `KAFKA_CONSUMER_METADATA_BROKER_LIST`, `KAFKA_CONSUMER_GROUP_ID`, `INGESTION_CONSUMER_GROUP_ID`, `INGESTION_CONSUMER_CONSUME_TOPIC` values pointing only to the test broker/topic.
- Correct `KAFKA_CONSUMER_AUTO_OFFSET_RESET=earliest` librdkafka override, **not** the invalid `KAFKA_CONSUMER_OFFSET_RESET` that mistakenly translates to `offset.reset` in the Rust consumer override parser.
- A **separate dummy HTTP health-only worker** on loopback which returns `/_ready=200`. It does **not** implement the Node worker's gRPC protocol. **No events are published** to the native consumer's dedicated topic, so the test cannot claim event processing or offset commits.
- The real Java Kafka `kafka-consumer-groups.sh --describe --group <test group> --state` command. Membership is accepted **only** when the exact test group appears in **Stable** state with **1** member. This is an independent Kafka broker-level proof beyond the Rust process's log claims.

All server endpoints are private to the Mac, no inherited project secrets, cloud endpoints, or real user data, and all owned Kafka, Rust and fake-worker processes are stopped and temporary storage removed afterward.

## Actual observed behavior (October 26, 2026)

**First attempt did NOT pass**: Kafka started but Rust failed to bind its local health endpoint. The issue was in the test harness environment: `KAFKA_CONSUMER_OFFSET_RESET=earliest` translates to an invalid librdkafka key `offset.reset`, causing early startup failure. The test harness was fixed (using `KAFKA_CONSUMER_AUTO_OFFSET_RESET`) **without editing product Rust code**, and the next actual run:

```sh
python3 -m tools.flind.qualify_native_consumer_kafka_group_wave119
```

**EXIT 0**, with `actual_native_rust_consumer_kafka_group_qualified=true`, `isolated_kafka_431_passed=true`, `real_kafka_431_group_join=true`, native loopback HTTP health bound, readiness gate observed a successful synthetic worker probe, and owned process cleanup successful. Native readiness readings included 503 before verified worker and 200 afterward. The broker-level test group is Stable with a single native Rust member.

```sh
python3 -m unittest -q tools.flind.test_native_consumer_kafka_group_wave119
```

The focused test repeats the real private Kafka membership proof and refuses missing binaries / external Kafka hosts / invalid qualification promotion.

## Strict evidence boundary / NO-GO

This proves **a real Rust consumer can connect to a real Kafka 4.3.1 broker and join a group while its configured HTTP worker probe becomes healthy**.

This does **not** prove its actual Rust→Node **gRPC** ingestion pipeline, event processing, Kafka acknowledgments and committed offsets, replay/recovery, tenant isolation, production ClickHouse tables, authenticated query API, dashboard or OAuth. The dummy worker only implements HTTP `/_ready`, and the Kafka topic for the native consumer is intentionally **empty**. The separate Kafka transport fixture creates synthetic CLI records on **a different topic**, and those are not attributed to this native Rust consumer.

Release remains **NO-GO** and Issue #82 remains open, with the repository private, inherited GitHub Actions disabled, no deployment, no paid cloud resources and all mandatory donor legal attribution preserved.
