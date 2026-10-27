# Flind Wave 188 — First-party-schema MergeTree durability in supported ClickHouse 25.12

## Real result — 27 October 2026: PASS

**Four independent ClickHouse 25.12.7.21 processes**, each launched fresh using `clickhouse local --path` with the *same isolated disk state*, successfully created a **MergeTree** persistent table, inserted four synthetic Flind events, closed, reopened and selected those exact original UUIDs, inserted one more synthetic event in a later process, and reopened again to validate **5/5 original UUIDs and corresponding team/event fields**. After the final restart, synthetic team 101 had 3 rows, team 202 had 2 rows, team 303 had 0 rows. On-disk MergeTree `store/*/checksums.txt` parts were present.

This is **not** the earlier Memory-engine-only proof of Waves177–183. Durable data was actually recovered after OS subprocess exit and independent ClickHouse process startup, within this single temporary Mac scratch directory. There was **no simulated power failure** and no real authenticated product API, Kafka ingestion or tenant authorization.

### Source and official version admission

The executable was obtained free from the official ClickHouse GitHub release `v25.12.7.21-stable`, asset `clickhouse-macos-aarch64`. The compressed official asset was **123,762,120 bytes**, SHA256 `e5be46727e773893b5786aaa3d28f5661a30179fe65e19096d8eb7d41a554fd6`, exactly matching the GitHub release's `sha256:` digest. Source: `https://github.com/ClickHouse/ClickHouse/releases/tag/v25.12.7.21-stable`.

The first-party Flind `posthog/settings/service_requirements.py` tracked Git blob was SHA-verified on pinned source commit `1905e9afb0f25f2685f042485b59f4c433403ffe` and declares ClickHouse `>=24.8,<=25.12`. The actual executable returned `ClickHouse local version 25.12.7.21 (official build)`. `posthog/clickhouse/hcl/roles/coshared/events_recent/tables.hcl` was independently verified from the same private Git source. Only its exact verified, six-column subset was used: `uuid UUID`, `event String`, `properties String`, `timestamp DateTime64(6, 'UTC')`, `team_id Int64`, `distinct_id String`. The temporary MergeTree's `ORDER BY (team_id,timestamp,uuid)` was introduced **only for this fixture**; it is **not** a claim that the production table's full DDL was applied.

**Important macOS packaging detail:** the official compressed macOS asset *self-expands when first invoked*, increasing its size from 123.8 MB to approximately 686.9 MB and changing its SHA256. A first attempt therefore failed closed after the asset was executed with a naïve post-execution digest check. The fixed tool hashes the original official download **while immutable**, creates an isolated fresh copy for runtime use, allows at most 45 seconds for first self-extraction, and then runs every ClickHouse SQL process with a separate hard timeout of 27 seconds. The source asset remains immutable and verifiable after the test. Another initial run's short 9-second bootstrap version timeout also failed safely; no SQL success was claimed until the final corrected run passed.

### Actual final receipt

`tools/flind/qualify_supported_mergetree_durable_wave188.py` completed **exit0**, about **34.04 seconds**, reporting:

- `official_supported_binary_attested=true`
- `first_party_events_schema_attested=true`
- `real_supported_mergetree_insert_qualified=true`
- `mergetree_persisted_across_four_processes=true`
- `synthetic_team_predicates_after_restart_qualified=true`
- `real_clickhouse_processes_executed=4`
- `synthetic_events_persisted=5`
- `synthetic_teams_checked=[101,202,303]`
- `disk_part_checksum_present=true`
- `native_kafka_to_clickhouse_qualified=false`
- `authenticated_tenant_isolation_qualified=false`
- `sdk_api_dashboard_qualified=false`
- `release_qualified=false`

The four ClickHouse processes confirmed initial data insertion (team101=2, team202=2), first complete UUID readback after restart, another insertion (team101=3), and final exact UUID/content checks after a fourth process and restart. Every subprocess had detached stdin, scratch-scoped output and source-verified fixed SQL, and used a 128MiB memory limit and max2 threads. Free-disk reserve was at least 5GiB. The script refuses unexpected existing data directories or output files, tampered release assets, wrong binary location/version, changed source schema, and unmarked scratch ownership.

**9/9 focused Python guard tests PASS** with `-W error::ResourceWarning`, covering official asset size/scope rejection, missing ownership marker, four-process bound, output overwrite refusal, preexisting persistent table-state refusal, fake cross-team UUID corruption and non-promotion of release flags. These focused tests are **additional** to the real four-process ClickHouse run; fake receipts do not substitute for the real integration receipt.

### Remaining release blockers

- The **real first-party Rust Kafka ingestion consumer** is not connected to the production Node pipeline or this persistent MergeTree table. Wave187 only used an original typed Rust Proto **test client**, Wave184 a real Rust consumer with a **test** gRPC server, and this Wave188 is source-backed local ClickHouse SQL independently.
- No real PostgreSQL migrations/rollback, authenticated tenant-level API security, full SDK→Dashboard/browser/desktop E2E, durable Kafka MV and native replay/resume, idempotence/exactly-once, or current-main release binaries and identity verification.
- Simple `WHERE team_id` SQL checks in the synthetic fixture do **not** prove authorization, tenant-level access-control enforcement or the full app's correctness.

**Issues #82 and #5 OPEN / Release NO-GO.** Repository remains PRIVATE, inherited GitHub Actions disabled, no publication/deployment, paid services/models or real user data. Mandatory upstream legal attribution must be preserved.
