# Wave 48 — Real local backend prerequisite check and honest NO-GO evidence

## Why this gate exists

Component and source tests were passing while the full Flind Django/API,
PostgreSQL, Redis, ClickHouse and capture/query stack had not been run.
The working Mac has eight GiB RAM and limited free disk space; the Docker
CLI exists but its daemon is not running. Opening the full inherited
multi-service Docker stack without a resource plan could impact unrelated
projects and does not guarantee a release-qualified Flind service.

## Safe, repeatable tool

Run from the Flind repository root:

    python3 tools/flind/qualify_backend_runtime.py --json

The stdlib-only preflight performs the following read-only operations:

- PostgreSQL local SELECT 1 with psql -X (no schema, migrations or writes)
- Redis PING to loopback 127.0.0.1:6379
- ClickHouse HTTP /ping to loopback 127.0.0.1:8123
- Django import availability in the active Python environment
- Docker daemon health as an OPTIONAL convenience indicator

Only the first four are required for local prerequisite readiness; Docker
is NOT a mandatory release requirement when native services are available.
The tool never starts containers, runs migrations, creates databases,
downloads code, sends credentials, checks an external host or provisions
services. The JSON contains no usernames, passwords or server response
bodies, and is suitable for a local evidence record.

Exit 0 means these basic prerequisites are present, NOT that Flind
is operational. Exit 2 means at least one requirement is blocked.
In both cases release_qualified remains false until real E2E evidence
covers ingest, async processing, data query, session/auth, permission
isolation, recovery and build/distribution.

## Executed Mac evidence (24 October 2026)

- PostgreSQL 17.9, read-only SELECT 1: PASS
- Redis local PING: BLOCKED (no successful local response)
- ClickHouse local HTTP ping: BLOCKED (no successful local response)
- Django import in active Python: BLOCKED (not installed)
- Docker daemon: UNAVAILABLE (optional)
- Overall prereq gate: BLOCKED, exit 2

These checks do not assert that no other remote/database deployment
exists; only that this local set of default endpoints is not ready.

## Automated test evidence

- 12/12 focused Python unittest checks pass: read-only PostgreSQL SELECT,
  timeout and missing executable, loopback Redis PING, ClickHouse HTTP
  with no redirects, explicit local-only Docker socket, missing Django,
  machine-readable nonzero results, and human optional/required statuses.
- Full Flind Python source regression suite: **345/345 PASS**.
- No schema migration, user data, external API or paid service was touched.

## Completion work

Provision an independently controlled, legally approved Flind backend,
then qualify a clean DB migration, ingest/capture to ClickHouse,
read/query parity, auth/OAuth redirect and scoped token exchange, tenant
isolation, failure recovery and desktop/mobile/browser smoke. Use this
preflight as a prerequisite only, not a substitute for any of these.

Keep the GitHub repository private, inherited Actions disabled; do
not publish/deploy or use paid providers without a separate decision.
