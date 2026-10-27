# Flind Wave 182 — Same native Rust Capture UUID read back from Kafka and supported ClickHouse

## Actual end-to-end synthetic native Capture event SQL proof — October 27, 2026

**PASS**: The previously compiled first-party Rust Capture server accepted a real synthetic HTTP event, ACKed its UUID, and the very same UUID was consumed from actual Kafka4.3.1 and inserted into actual ClickHouse25.12.7.21 **Memory engine**, and then returned by a SQL SELECT as the exact ACKed UUID. This is a stronger, *single-event-contiguous* proof than Waves179–181, which proved two distinct synthetic fixture paths separately.

This is **still not** the real Flind ingestion-consumer/Node gRPC worker or a durable ClickHouse materialized Kafka ingestion engine. The Kafka→ClickHouse hop here is explicitly a private bounded Python test bridge. No end-user authorization or dashboard execution.

### Components actually exercised
1. An isolated, private **Apache Kafka 4.3.1 KRaft** broker/controller with 127.0.0.1-only listeners, private topics/groups, bounded 384MiB JVM heap, 3GiB disk reserve and marker-owned storage, using the previously cached official Kafka distribution. No production broker.
2. Previously compiled **Rust Capture** from an earlier Flind source stage, pinned by **exact SHA-256 `a255ae78e180d9488b4efc126b7d2c8378e209640ee36d7c28f491bb40693379`**. It was *not freshly built/attested from latest main*. It accepted a synthetic POST at `/i/v1/analytics/events` and returned the successful per-UUID acknowledgement.
3. A separately spawned **Redis 7.4.11**, within the first-party declared Redis `>=7,<8` compatibility range, ephemeral loopback-only, no AOF/RDB persistence, capped 32MiB memory.
4. A native Kafka consumer retrieved the exact UUID, `$pageview` event, synthetic token and distinct ID, and only then could invoke the test bridge callback; the UUID passed into the ClickHouse bridge was bound to the Rust HTTP ACK.
5. The bridge statically verified the first-party Git-tracked Flind `events_recent` HCL field/type subset and `service_requirements.py` compatibility requirements on pinned source commit `1905e9afb0f25f2685f042485b59f4c433403ffe`. Local ClickHouse **25.12.7.21** passed source range `>=24.8,<=25.12`.
6. **One exact native Capture Kafka event** was inserted through `CREATE TABLE ... ENGINE=Memory` and `INSERT INTO`, followed by actual `WHERE team_id=101` and `WHERE team_id=202` SQL checks and a direct `uuid,team_id,event` readback for team 101. The selected ClickHouse UUID **exactly matched** the Rust HTTP ACK; the single synthetic team101 event existed; synthetic team202 yielded no result.

### Validation and iteration
- Initial actual run failed closed with `native_fixture_path_mismatch`; that first-party Rust Kafka envelope did not expose the original optional HTTP `$pathname` through `properties` as the test initially assumed.
- A second actual run failed closed with `native_properties_not_an_object`; the original native envelope's optional `properties` was not a JSON object. The adapter was corrected to accept omitted/null optional properties, while validating exact UUID, event, synthetic token, synthetic distinct ID and refusing any explicitly client-supplied `team_id`; it **never invents** a pathname when absent.
- The **final standalone script** `tools/flind/qualify_cached_native_capture_clickhouse_wave182.py` on this exact proposal completed **exit 0** (~34.7 seconds) with `native_capture_http_kafka_clickhouse_uuid_pass=true`, `native_event_inserted_rows=1`, `owned_capture_stopped=true`, `owned_redis7_stopped=true`, `owned_kafka_process_stopped=true`, `owned_kafka_scratch_removed=true`.
- Existing Wave179's independent synthetic Kafka→ClickHouse Memory fixture was also exercised and qualified on the *same private broker*, but was **not substituted for or confused with** the native Capture event.
- **37/37 tests PASS** across Wave179, Wave180, Wave181 and Wave182 focused Python suites with `-W error::ResourceWarning`. Tests cover refusal of mismatched/forged ACK UUID, token, event or distinct ID; rejection of source-supplied numeric tenant; optional native properties compatibility; refusal of unsupported ClickHouse26, unsafe Kafka destinations and false release flag promotion.
- The refusal diagnostic codes are drawn exclusively from a static allowlist and do not print the Kafka payload, authorization headers or unbounded exception messages.

### Synthetic tenancy limitation

`team_id=101` in this tool is a **fixed synthetic-only test mapping** conditioned on an exact synthetic token. It is **not actual tenant authentication or product authorization**. No user-supplied team field is accepted. Team202 being empty is a simple query-scope smoke, **not proof of real tenant isolation**.

### What remains unqualified

- Real Rust **ingestion consumer** reading from Kafka and real **Node gRPC worker** successfully processing/committing the ACKed native Capture event.
- Persistent ClickHouse MergeTree/Kafka materialized engine, replay, retention, offset fencing, failure/recovery, distributed tenant-scoped query API and authenticated dashboard.
- SDK→real authenticated API→browser/desktop/mobile workflows; full PostgreSQL migration upgrades/rollback beyond scoped single migration; first-party identity/installer/package audit and owned OAuth/PKCE.
- This still uses a **cached Rust Capture binary** from earlier development and the pinned older source Git tree, **not** a brand-new fully-built executable from current GitHub main.

**Release #82 and identity #5 remain OPEN, Release NO-GO.** Repository stays PRIVATE, inherited GitHub Actions disabled, no deployment, publication, paid services or actual user data; all legally required third-party attribution preserved.
