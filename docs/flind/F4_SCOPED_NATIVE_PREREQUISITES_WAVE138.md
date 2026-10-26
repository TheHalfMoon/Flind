# Wave 138 — Simultaneous isolated native backend prerequisites

## Why this wave

The read-only production/default-port backend gate continued to report Redis and ClickHouse unreachable, although compatible native binaries were already available locally. That gate only checks live default ports and should not be treated as a statement about whether Flind can run process-owned Redis/ClickHouse. Rather than start shared default-port services or install another monorepo, this wave exercises the actual pinned database engines on private random loopback ports with bounded memory/disk.

## Reproducible command

Run on the connected Mac from the repository root using the already present compatible binaries:

```bash
PYTHONPATH=. python3 -m tools.flind.qualify_native_prereqs_wave138 \
  --redis-bin /tmp/flind-wave74-services/redis-7.4.11/src/redis-server \
  --clickhouse-bin /tmp/flind-wave74-services/clickhouse-25.12.7.21-macos-arm64 \
  --json
```

This is a test of **three process-owned native prerequisites only**, not a Flind installation or release qualification. This module rejects absent binaries or less than 13 GiB free disk. PostgreSQL 17 runs with a disposable temporary data directory/DB, auth and randomized nondefault port, and verifies a rolled-back SQL transaction. Redis 7.4.11 uses a private loopback-only, no-persistence instance with bounded memory and PING/SET/GET/DEL checks. ClickHouse 25.12.7.21 uses its temporary memory-limited instance and confirms a three-row SQL roundtrip with count 3 and sum 60. The modules' existing `finally` paths stop each owned server and dispose its test files. Their versions must match Flind's actual source service specs; no requirement is relaxed to make the test pass.

## Execution on 2026-10-26

Fetched the exact GitHub branch, copied the new qualifier into the existing *clean sparse checkout temporarily* and executed it as a package module with `PYTHONPATH=.`. The first direct-script invocation, without module search path, correctly failed at import before launching any service; the supported module invocation **PASS, exit 0** in around four seconds. The temporary source file was removed after the test.

Live output:

- `three_native_prerequisites_qualified=true`
- `postgres_scoped=true`, `postgres_transaction_rolled_back=true`, `postgres_rows=3`, `postgres_sum=14`
- `redis_scoped=true`, `clickhouse_scoped=true`, `clickhouse_rows=3`, `clickhouse_sum=60`
- `all_source_versions_supported=true`
- `django_dependency_lock_qualified=false`; **188 applicable direct dependencies missing**, **11 installed with mismatched versions**
- `django_migrations_qualified=false`, `real_sdk_ingestion_qualified=false`, `real_worker_qualified=false`, `query_api_qualified=false`, `tenant_auth_qualified=false`, `release_qualified=false`.

The Mac has only ~8 GiB RAM and ~16 GiB free disk. Do not run an unrestricted multi-service Docker stack or attempt an uncontrolled full dependency install here. This test did not touch shared PostgreSQL on 5432 or any user data and involved no paid/cloud services.

## Next release-critical work

Qualify pinned Python **3.14.7** and its 201 applicable direct dependencies within a separately provisioned, resource-safe no-cost environment, then migrate isolated Flind schemas, boot actual Django/API plus Node/Rust ingest workers, execute synthetic SDK→capture→Kafka/ClickHouse→tenant-filtered query→Dashboard E2E and failure recovery. Keep issue #82 open and release **NO-GO**. No publication/deployment; repository remains private with inherited Actions disabled, legal notices preserved.
