# Wave 51 — Qualify actual service versions, not just reachable ports

## Finding

Wave 50 proved real temporary Redis and ClickHouse read/write and the
five underlying local prerequisites. However the temporary engines were
Redis 8.10.2 and ClickHouse 26.10.2.103, while Flind's own
posthog/settings/service_requirements.py requires:

- PostgreSQL >=14.0.0
- Redis >=7.0.0,<8.0.0
- ClickHouse >=24.8,<=25.12

A successful ping, SELECT, or toy table does not establish whether
Flind supports that engine version.

## Change

- Extract all three source version requirements from Python AST without
  importing Django, Celery or the backend module.
- Require valid specs and all three services. Unknown, duplicate, missing
  or invalid requirements fail closed.
- Check local PostgreSQL with SHOW server_version, Redis with bounded
  RESP INFO server, and ClickHouse with direct HTTP SELECT version().
- Compare with the source spec including semantic_version.SimpleSpec's
  partial-version semantics (the whole 25.12 minor line is allowed).
- Expose separate stack_prerequisites_passed, service_versions_supported
  and app_runtime_compatible. Healthy but incompatible services produce
  a nonzero stack gate exit code.
- Allow explicitly selected temporary Redis and ClickHouse executable
  paths. Never replace globally installed versions or leave a daemon.
- release_qualified remains false even when all versions are compatible.

## Executed macbook evidence, October 24, 2026

Baseline reachable but out-of-contract versions:
- PostgreSQL 17.9 PASS.
- Redis 8.10.2 fails version gate despite PING/SET/GET/DEL PASS.
- ClickHouse 26.10.2.103 fails version gate despite SQL readback PASS.
- app_runtime_compatible=false, exit 2.

Compatible binaries installed only for the temporary local tests:
- Redis 7.2.12 compiled from official Redis archive without replacing Brew.
- ClickHouse 25.11.9.34 from the official GitHub release; SHA256
  db4cf7d5460cdaa445635227a641f231c098f961030682a88e3080d1bf84ecbf
  matched the published digest.
- PostgreSQL 17.9 >=14: PASS.
- Redis 7.2.12 >=7,<8: PASS.
- ClickHouse 25.11.9.34 >=24.8,<=25.12: PASS.
- Python 3.14.7 and Django 5.2.18 import: PASS.
- PostgreSQL, Redis, ClickHouse primitives: PASS simultaneously.
- Temporary child processes and data directories cleaned.

Reproduce using the pinned Python interpreter:

    python tools/flind/qualify_ephemeral_stack.py --json \
      --redis-bin /tmp/flind-redis7-src/redis-7.2.12/src/redis-server \
      --clickhouse-bin /tmp/flind-clickhouse25/clickhouse-macos-aarch64

These local temporary paths are not embedded in product code.

## Remaining release blockers

Real Flind Django app startup, schema migrations, Celery, Kafka/event
ingestion, SDK capture/query parity, OAuth, tenant isolation and real
browser/desktop/mobile E2E remain issue #82 acceptance gates. No
production release, deployment, paid services, persistent data or user
credential submissions. Repo private; inherited Actions disabled.
