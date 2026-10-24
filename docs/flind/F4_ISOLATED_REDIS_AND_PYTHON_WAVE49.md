# Wave 49 — Real Redis component smoke and exact Python prerequisites

## Baseline problem

Wave 48 accurately established PostgreSQL availability, but the checked
Python interpreter was 3.13.5 while the repository explicitly requires
3.14.7. Django was absent; Redis was not installed/running. This version
mismatch could be masked by merely installing Django under another Python.

## Implemented

- Python prerequisite checker now parses project.requires-python from the
  repository's pyproject.toml with Python's standard library and compares
  the exact major/minor/micro of the **running** interpreter. Missing or
  nonexact pins fail closed. This is required in the normal backend preflight.
- Backend preflight accepts --redis-port, always using IPv4 loopback.
  The default remains 6379; no existing server is started or modified.
- Added qualify_ephemeral_redis.py, a genuine, no-persistence Redis server
  test that starts a dedicated process on a randomly selected loopback port
  with a 64 MiB memory cap and a temporary data directory.
- Performs real Redis PING, SET, GET, DEL and read-after-delete on that
  test-only instance, then terminates it even when a check fails.
- Captures the normal backend prerequisite results *while that isolated
  instance is running*. The Redis component smoke can pass while backend
  prerequisites and release E2E remain blocked.
- Unit tests cover bounded RESP protocol parsing, no-redirect safety
  indirectly via Wave 48, no-persistence command flags, process cleanup,
  explicit Python version pin and JSON/exit behavior.

## Reproduction

From the Flind checkout:

    python3 tools/flind/qualify_backend_runtime.py --json
    python3 tools/flind/qualify_ephemeral_redis.py --json

Use a supported Python 3.14.7 virtual environment for the first-party
backend preflight. No Redis process, container or external service
persists when the isolated Redis test completes.

## Mac evidence, 24 October 2026

On the authorized macbook, installed Redis 8.10.2 from a free Homebrew
bottle, without starting the launch-at-login Redis service. Created a
temporary, isolated uv 0.13.5 toolchain and a managed Python 3.14.7 with
Django 5.2.18 matching uv.lock, all under /tmp. The existing system
Python and uv executables were not replaced.

- Real temporary Redis PING/SET/GET/DEL/read-after-delete: PASS.
- Python 3.14.7 exact pin: PASS in the isolated virtual environment.
- Django 5.2.18 import: PASS in the isolated virtual environment.
- PostgreSQL read-only SELECT 1: PASS on existing localhost database.
- Redis loopback ping: PASS *only while the temporary server was alive*.
- ClickHouse HTTP ping: BLOCKED.
- Docker local daemon: unavailable, OPTIONAL.
- Focused source and protocol regression tests: **23/23 PASS**.
- Full Flind Python source suite: **356/356 PASS**.
- release_qualified: false (regardless of component checks).
- Redis process exited, no launch-at-login service was enabled, no
  project databases were migrated or modified.

## Outstanding release blockers

An isolated Redis roundtrip and Django import do not prove that the Flind
Django app starts, migrations apply, workers process events, ClickHouse
accepts ingestion, queries reflect events, OAuth tokens work or tenants
are isolated. Full project dependency installation and ClickHouse
integration require a separate resource-qualified environment. Use the
existing issue #82 for acceptance and E2E receipts.

No publishing, deployment, paid services or credential egress. GitHub
repository remains private with inherited Actions disabled and required
attribution preserved.
