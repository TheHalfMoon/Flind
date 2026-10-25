# Wave 73 — Select compatible offline/local service binaries explicitly

Wave 72 proved that PostgreSQL 17, Redis 8.10.2 and ClickHouse
26.10.2 can run together locally with scoped Django framework session
migrations, but correctly BLOCKED compatibility because Flind's
requirements demand Redis 7.x and ClickHouse 24.8–25.12.

The isolated three-service qualifier now accepts **optional explicit
local executable paths**:

```sh
python -m tools.flind.qualify_service_triad_wave72 --json \
  --redis-bin /absolute/local/path/to/redis-server \
  --clickhouse-bin /absolute/local/path/to/clickhouse
```

This permits multiple locally installed versions without replacing
running system services or relying on PATH. The selected file must
exist at an absolute path and be executable before any service or
migration process is launched. Invalid, missing, nonexecutable or
relative paths fail closed without allocating a PostgreSQL cluster.
If no overrides are supplied, the existing default local binaries
are used.

These flags do not install or fetch software. They do not change
required version ranges, bypass Redis/ClickHouse version checks, or
start daemons outside the bounded local ephemeral services. Choose
binaries from a known trustworthy local installation before use.

## Evidence, October 25, 2026

- 12/12 Wave 72–73 focused version, routing and path-guard tests PASS.
- 48/48 combined backend-service and scoped auth/session unit tests PASS.
- Invoking the real qualifier with a missing executable was rejected
  before launch, returned an all-false receipt and exit code 2.
- The initial real Mac Redis 8.10.2 and ClickHouse 26.10.2 versions
  are still incompatible. **No compatible alternative binaries were
  installed or tested**.
- No full Django schema, Flind SDK ingestion, Kafka path, OAuth,
  tenant isolation, UI or release qualification.

TheHalfMoon/Flind stays private. Inherited Actions stay disabled.
No publication, deployment, paid cloud or removal of required source
attribution. Issue #82 remains open.
