# Wave 95 — Real version-qualified Kafka → ClickHouse synthetic relay

## What changed

Wave 85 validated live Kafka 4.3.1 transport and a temporary ClickHouse Memory-table readback with exactly three fixed synthetic events from two teams. Its original live test was previously unrun, and its default `clickhouse` executable on the Mac is version 26.10.2, while Flind's source contract allows ClickHouse `>=24.8,<=25.12`.

The new `tools/flind/qualify_supported_kafka_clickhouse_wave95.py` adds a separate, explicitly version-admitted real-service qualification without expanding the application's supported version range.

Before starting Kafka, it:
- Reads the ClickHouse requirement from Flind's checked-in backend settings using the existing source AST parser.
- Requires an absolute executable path and a successful, bounded local `--version` check matching that source requirement.
- Fails closed without launching Kafka or ClickHouse for missing or incompatible binaries.

After successful Kafka publish/consume, it launches the specifically admitted ClickHouse binary in the existing disposable, memory-bounded, loopback-only service wrapper. It independently checks `SELECT version()` against the source version range **on the running server** before relaying the actual Kafka-consumed records. It verifies exact count, row values and team-specific aggregates through the existing Wave 85 relay. All processes and temporary data are removed.

This remains a **synthetic CLI→temporary ClickHouse test**, not application SDK ingestion, the production Kafka consumer, production event schema, authenticated tenant authorization, or the user-facing dashboard.

## Real executable evidence — October 25, 2026

Source service version requirement: `>=24.8,<=25.12`.

- Kafka: actual official Apache Kafka **4.3.1** KRaft binary, loopback-only private broker.
- Compatible ClickHouse: actual **25.12.7.21** macOS arm64 executable, isolated temporary Memory table.
- Real command:

```sh
python3 -m tools.flind.qualify_supported_kafka_clickhouse_wave95 \
  --kafka-home /tmp/flind-kafka-4.3.1/kafka_2.13-4.3.1 \
  --clickhouse-bin /tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64 \
  --json
```

- Result: `supported_kafka_clickhouse_synthetic_relay_qualified=true`; `native_kafka_transport_passed=true`; `supported_clickhouse_runtime_passed=true`; `exact_synthetic_event_readback_passed=true`; `synthetic_event_count=3`.
- Negative *live* command with system default ClickHouse **26.10.2** exited **2** and refused the binary **before starting Kafka**.
- 39/39 targeted unit tests covering Waves 83–85 and 95 PASS. The new Wave 95 tests include source-version refusal, hostile/modified fixture refusal, forged component receipts, mismatched running version, real integration callback path and permanent release flag refusal.
- Real run returned exit code **0**, and process inspection showed no leftover Kafka or temporary ClickHouse service.
- No paid providers, deployments, release artifacts or publication.

## Hard limits and next gates

No production Flind SDK HTTP capture→native consumer→ClickHouse event schema→query API→browser evidence has been produced. Nor have full Django migrations, OAuth/tenant authorization, full TypeScript production build or Playwright UI E2E been qualified. Release stays **NO-GO** under Issue #82. Source repository remains private, inherited GitHub Actions disabled, and original required legal attribution preserved.
