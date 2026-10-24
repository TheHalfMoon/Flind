# Wave 50 — Real temporary ClickHouse HTTP and simultaneous prerequisites

## Why

Wave 49 proved a real Redis-only component and Python/Django availability.
The remaining ClickHouse requirement had not been exercised. An isolated
ClickHouse version and local engine query are not equivalent to an HTTP
server with storage/query, and a sequence of nonoverlapping service checks
is not simultaneous backend-prerequisite qualification.

## Implemented

- ClickHouse local HTTP port can be explicitly selected by a caller of the
  read-only preflight. It never sends data outside 127.0.0.1.
- tools/flind/qualify_ephemeral_clickhouse.py starts a standalone official
  ClickHouse binary with a generated XML configuration in a private temporary
  directory. Its HTTP listener and user ACL are loopback-only.
- ClickHouse has a 512 MiB server memory limit, default profile queries
  limited to 128 MiB, a fixed 16-thread background merge pool so ClickHouse
  sanity checks pass, and separate temporary data, logs and user-files paths.
  There is no external container, cloud service or persistent user data.
- A direct HTTP client (no redirects) verifies GET /ping, SELECT 1, then
  executes CREATE TABLE with Engine=Memory, INSERT three rows, SELECT
  count()/sum() and DROP TABLE. Expected result: count=3, sum=60.
- Isolated Redis (Wave 49) and ClickHouse now run concurrently via
  tools/flind/qualify_ephemeral_stack.py while the shared read-only
  Python/Django/PostgreSQL/Redis/ClickHouse prerequisite check executes.
- Both child processes are terminated in finally and temporary data
  directories removed. No login daemon, DB migrations, credentials,
  external API calls or scheduled jobs are created.

## Reproduction

With repository-pinned Python 3.14.7, Django 5.2.18, local PostgreSQL
and free Redis/ClickHouse binaries:

    python tools/flind/qualify_ephemeral_clickhouse.py --json
    python tools/flind/qualify_ephemeral_stack.py --json

For the normal local service prerequisite report:

    python tools/flind/qualify_backend_runtime.py --json

When temporary children exit, the normal report correctly says local
Redis/ClickHouse are unavailable unless another service has been started.

## Actual macbook evidence, 24 October 2026

- Official ClickHouse 26.10.2 binary installed and verified locally.
- ClickHouse temporary HTTP ping, SELECT/CREATE/INSERT/SELECT/DROP: PASS.
- Count/sum read-back: 3 rows, total 60; memory-only test table.
- Temporary Redis PING/SET/GET/DEL/read-after-delete: PASS.
- Python 3.14.7 and locked Django 5.2.18 import: PASS.
- Local PostgreSQL 17.9 SELECT 1: PASS.
- Five of five required local backend prerequisites PASS simultaneously.
- Docker daemon unavailable, correctly OPTIONAL.
- release_qualified remains false. All temporary processes stopped.
- The full-source regression suite must pass before PR merge.

## What this does NOT establish

Real Flind Django settings/app have not been started successfully, Flind DB
migrations have not been qualified, Redis consumers/background workers are
not running, ClickHouse event ingestion/queries are not connected to SDK
data, and auth/OAuth/tenant isolation, replay, browser and device E2E
remain untested. This proves underlying primitives only.

Launch readiness remains NO-GO until issue #82 is qualified with live
application-layer E2E. Repository remains private, inherited Actions
disabled; nothing published or deployed and no paid services used.
