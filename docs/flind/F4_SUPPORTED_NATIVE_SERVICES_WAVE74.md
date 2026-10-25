# Wave 74 — Actual compatible native Redis and ClickHouse on macOS

## Blocker removed at the isolated component boundary

Previous Wave 72 tests proved PostgreSQL / Redis / ClickHouse coexistence
and real Django framework auth/session migrations, but used the machine's
default incompatible Redis 8.10.2 and ClickHouse 26.10.2.103.

On October 25, 2026, Wave 74 used **separate versioned executables in
`/tmp/flind-wave74-services`** on the authorized Apple Silicon Mac:

| Service | Observed actual version | Contract | Result |
| --- | --- | --- | --- |
| PostgreSQL | 17.9 | >=14 | PASS |
| Redis | 7.4.11 | >=7,<8 | PASS |
| ClickHouse | 25.12.7.21 | >=24.8,<=25.12 | PASS |

Redis 7.4.11 was compiled from its official 3.4 MiB source archive at
`https://download.redis.io/releases/redis-7.4.11.tar.gz`, with a
local SHA-256 check of the downloaded tarball:
`3c266ece0abd54ed3b1c912c6eb86b7508cf382cb690ee6649d3843f018f6357`.
It was built using existing Apple C tools and libc without installing
or replacing the Homebrew Redis 8 daemon.

ClickHouse was downloaded from the **official GitHub release**
`ClickHouse/ClickHouse v25.12.7.21-stable`, asset
`clickhouse-macos-aarch64`. The 123,762,120-byte downloaded file
matched the release asset's published SHA-256 digest exactly:
`e5be46727e773893b5786aaa3d28f5661a30179fe65e19096d8eb7d41a554fd6`.
The macOS executable expanded its content on first launch; its
**post-first-run file size and digest differ**, so validate the original
download before first execution, not by assuming its unpacked executable
will hash like the compressed release asset. Observed runtime:
`ClickHouse local version 25.12.7.21 (official build)`.

## First actual three-service PASS

The existing `tools/flind/qualify_service_triad_wave72.py` probe
was run with Wave 73's explicit paths. It created its own private
PostgreSQL cluster; ran real `auth` and `posthog_session` Django
migrations; nested Redis with temporary writes and ClickHouse with
temporary SQL readback; and destroyed all temporary test services.

The exact-lock Python 3.14.7 environment passed its 201 direct
dependency pins. Its JSON receipt confirmed all of:

- `exact_python_lock_passed=true`
- `postgres_17_isolated_passed=true`
- `framework_auth_session_schema_passed=true`
- `redis_isolated_passed=true`
- `clickhouse_isolated_passed=true`
- `clickhouse_http_sql_readback_passed=true`
- `redis_and_clickhouse_overlapped_postgres=true`
- `three_service_reachability_passed=true`
- **`service_versions_qualified=true`**
- **`three_service_scoped_auth_qualified=true`**

This replaces the previous service-compatibility blocker with real,
auditable native evidence, without changing product version requirements.
The two selected binaries were used only within the existing disposable
service wrappers. The system's default Redis 8/ClickHouse 26 binaries
and shared PostgreSQL service were untouched.

## Reproducing (only after manually provisioning trusted binaries)

Run from the complete private Flind checkout with the locked runtime:

```sh
python -m tools.flind.qualify_local_binaries_wave74 --json \
  --redis-bin /absolute/path/to/redis-server-7 \
  --clickhouse-bin /absolute/path/to/clickhouse-25

python -m tools.flind.qualify_service_triad_wave72 --json \
  --redis-bin /absolute/path/to/redis-server-7 \
  --clickhouse-bin /absolute/path/to/clickhouse-25
```

The new quick binary preflight **does not** start services or claim
full application qualification. It reads exact source-defined version
constraints and runs only version commands from explicitly selected
executables. It never downloads, installs or changes system services.
Absolute paths and executable bits are required.

## Still NOT qualified

- Full Django migration graph, reversible/idempotent migration proof.
- Actual SDK -> Flind authenticated/synthetic ingest -> async/Kafka ->
  ClickHouse -> query API -> visible dashboard readback.
- OAuth/PKCE, token refresh/revoke, organization and tenant isolation,
  failure/recovery and desktop/mobile/browser E2E.

All remain `false` on the live triad receipt. Release remains
**NO-GO**. Issue #82 must remain open. Repo stays private,
inherited GitHub Actions disabled, no deployment, publication, paid
cloud or removal of mandatory legal attribution.
