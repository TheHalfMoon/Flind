# Flind Wave 189 — Real Kafka 4.3.1 → version-supported persistent ClickHouse MergeTree

## Verified real result (27 October 2026): PASS

An **actual private Kafka 4.3.1 KRaft broker** produced and acknowledged three entirely synthetic Flind messages. A second actual **Confluent Kafka consumer group**, with automatic commits disabled, independently consumed and exactly validated those three messages from the original Kafka topic. A bounded **Python synthetic-only bridge**, not the production Flind Rust Kafka ingester or Node batch worker, transformed their source-compatible fields, inserted all three into an **actual on-disk MergeTree** backed by **official ClickHouse25.12.7.21** and the Git-verified six-column Flind events schema, shut down that ClickHouse process, **opened a separate independent ClickHouse process** on the same disk state, and verified all three exact synthetic UUID/event/team values.

**Only after the real second ClickHouse process had verified persisted disk data did the test Kafka consumer issue `commit(asynchronous=False)`.** Once the extension returned, the owned Kafka broker was stopped and its marker-owned ephemeral scratch deleted. This proves the sequencing of *this one synthetic test consumer group* relative to disk readback; it **does not** establish crash recovery, exactly-once product behavior, or persistence of that isolated broker's offset after broker deletion.

### Observed original integration receipt

`tools/flind/qualify_real_kafka_durable_mergetree_wave189.py` exited **0**, elapsed approximately **55.5 seconds**, and reported:

- `official_supported_clickhouse_attested=true`
- `real_kafka_to_durable_mergetree_relay_qualified=true`
- `actual_kafka_records_persisted=3`
- `kafka_offset_commit_after_disk_qualified=true`
- `owned_kafka_process_stopped=true`
- `owned_kafka_scratch_removed=true`
- `real_first_party_rust_consumer_qualified=false`
- `real_node_production_driver_qualified=false`
- `authenticated_tenant_isolation_qualified=false`
- `sdk_api_dashboard_qualified=false`
- `release_qualified=false`

The stored event set was team101=2, team202=1, missing team303=0, and three UUIDs matched the exact Kafka-consumed validated records after a separate ClickHouse process restart. Actual MergeTree on-disk part `checksums.txt` files were present.

The first-party `posthog/settings/service_requirements.py` Git-backed source declares ClickHouse `>=24.8,<=25.12`; actual binary version is **25.12.7.21**, and the official compressed macOS arm64 GitHub release asset is SHA256 `e5be46727e773893b5786aaa3d28f5661a30179fe65e19096d8eb7d41a554fd6`. It is verified **before** being copied and self-expanded into scratch. The six source-backed `events_recent` column types are taken from Flind's tracked `posthog/clickhouse/hcl/roles/coshared/events_recent/tables.hcl`, source commit `1905e9afb0f25f2685f042485b59f4c433403ffe`. This source snapshot was used for compatibility, **not** a claim that the whole latest main was rebuilt into production executables.

Implementation reuses the already qualified Wave179 **actual ephemeral Kafka4.3.1** harness with its existing synthetic-memory-relay test. Its optional private-broker callback starts the **second independent Kafka consumer group** and writes **that group's exact Kafka data** to persistent MergeTree (not an unrelated Python hardcoded fixture). The original Wave179 consumer group is separate. Production Flind Kafka topics, production datasets and actual user events are never accessed.

### 11/11 guard/unit tests PASS

`tools/flind/test_real_kafka_durable_mergetree_wave189.py` completed **10/10 PASS** with `-W error::ResourceWarning`:
- Validates exact input fixture and rejects reordered/modified Kafka records or team IDs.
- Rejects ClickHouse processes outside the exact two-process budget and existing output paths without overwriting files.
- Refuses scratch without an ownership marker.
- Rejects mismatched persisted UUID readbacks after a mock restart and checks the simulated successful count/UUID readback.
- Uses a fake, controlled Confluent consumer to prove **NO offset commit** when disk persistence fails, and **exactly one commit** only when persistence returns a valid success receipt.
- Confirms even a fully passing synthetic receipt **does not promote native worker, production Node pipeline, tenant authentication, SDK/browser E2E or release qualification**.

The full real integration was executed independently of these mocks and completed exit0. Following addition of a fail-closed **exact persistent-readback receipt admission** before Kafka commit, the final proposed code was re-run on a **second entirely fresh Kafka/ClickHouse scratch** and completed exit0 again (approximately **75.5 seconds**); 3 Kafka records persisted, explicit post-disk offset commit true, and owned Kafka process/scratch stopped and cleaned. A new eleventh guard test rejects a forged empty `disk_persist_and_reopen` success receipt and verifies **zero Kafka offset commits** in that case. All processes use synthetic events, bounded memory and disk resources, loopback-only Kafka interfaces, and marker-owned temporary folders.

### Strict limitations / release gates

This is **Python test bridge Kafka→ClickHouse**, not the **original Rust `ingestion-consumer` → production Node `StreamIngestDriver`**. Wave184's nine original Rust Kafka/test-gRPC scenarios, Wave186's original Node gRPC wire server, Wave187's original typed Rust→Node test-client protocol and Wave188's supported MergeTree durability all passed individually, but have **not** yet been combined into an actual all-first-party production event path. This test does not establish native ClickHouse Kafka engine/materialized views, concurrent ingesters, idempotency/deduplication/exactly-once, broker crash+replay, authenticated tenants, real API/dashboard/SDK or a product release. The MergeTree table uses a source-verified six-column **subset** and fixture-specific sort key, not the complete production DDL.

**Release issue #82 remains OPEN and identity issue #5 remains OPEN — Release NO-GO.** Repository PRIVATE, inherited GitHub Actions disabled; no publication/deployment, paid compute/models, actual customer data, or removal of legally required upstream attribution.
