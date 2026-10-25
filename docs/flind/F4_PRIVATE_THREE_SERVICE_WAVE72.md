# Wave 72 — Same-lifetime PostgreSQL, Redis and ClickHouse qualification

## Objective

Previous backend probes qualified individual isolated services separately.
The older two-service stack also used an independent PostgreSQL preflight at
the default system port, **not** the PostgreSQL 17 cluster it was supposed to
represent. Wave 72 performs a new, explicitly scoped integration on the
authorized Mac, without touching installed databases or starting services
outside the test process.

The harness nests all three existing temporary-service utilities:

1. A private SCRAM-authenticated PostgreSQL 17 database on random localhost
   port; real CREATE/INSERT/SELECT/ROLLBACK component proof.
2. While that database is alive, the existing bounded Django migration tool
   applies `auth` then `posthog_session` to the SAME ephemeral database,
   and independently reads migration/table receipts.
3. PostgreSQL stays running while a private no-persistence, loopback Redis
   starts and completes PING/SET/GET/DEL/read-after-delete.
4. With both servers still alive, a memory-bounded, loopback ClickHouse
   starts and completes CREATE/INSERT/SELECT/DROP on a temporary table.
5. All three service processes and all ephemeral test files are torn down.
   The PG wrapper destroys credentials, data and test database after return.

## Two separate admission gates

**Reachability** reports actual service overlap, SQL readbacks and scoped
Django framework authentication/session migration success.

**Compatible backend admission** additionally compares observed PostgreSQL,
Redis and ClickHouse versions against the actual source file
`posthog/settings/service_requirements.py`. This is fail-closed.
Never equate a successful Redis/ClickHouse SQL ping with support for the
installed server's major version.

The project's version contracts at the time of this wave are:

- PostgreSQL: 14.0.0 or later
- Redis: 7.x (at least 7.0.0, strictly below 8.0.0)
- ClickHouse: 24.8 through 25.12 inclusive

The machine under test currently has Redis 8.10.2 and ClickHouse 26.10.2.
Do **not** relax these bounds or suppress warnings just to make the
qualification green. Compatible isolated binaries would be required for
a full pass; the backend may also need legitimate compatibility work.

## Evidence — October 25, 2026

- Exact frozen Python 3.14.7 direct dependency lock: 201/201 PASS.
- First live test successfully started and tested all three private
  services in overlapping lifetimes; scoped real `auth` and
  `posthog_session` migrations PASS; Redis and ClickHouse primitives PASS.
- The first success proves **service overlap and scoped Django framework
  migrations**, not release fitness or supported versions.
- Extended focused regression suite: 43/43 initial PASS; version admission
  was added with both compatible and incompatible scenario assertions.
- Actual repeated version-aware run on isolated test services:
  `three_service_reachability_passed=true` and
  `framework_auth_session_schema_passed=true`.
- The live version check read PostgreSQL `17.9 (Homebrew)`, Redis `8.10.2`,
  ClickHouse `26.10.2.103`. Comparing source-defined requirements returned
  `service_versions_qualified=false`,
  `three_service_scoped_auth_qualified=false`, and
  `release_qualified=false`. This is the correct **blocked** result,
  not a failed SQL readback. No requirement was changed.
- The runtime test destroyed all temporary services and credentials.
- No SDK capture, Kafka/ClickHouse application ingestion, authenticated
  HTTP login, multi-tenant isolation, full Django schema or browser E2E.
  These must remain explicitly FALSE in all reports, even if versions match.

## Running

In a complete Flind checkout with exact Python dependencies and the local
three server binaries:

```sh
python3 -m unittest tools.flind.test_service_triad_wave72 -q
python -m tools.flind.qualify_service_triad_wave72 --json
```

The tests have real, positive and negative version-admission assertions.
Receipt never includes ephemeral passwords, bearer keys, connection URLs,
system service paths, customer records or logs. Nothing is deployed or
published; mandatory legal attribution is untouched. The repo remains
private with inherited GitHub Actions disabled.

Issue #82 stays OPEN until the actual full application, compatible
services, and end-to-end SDK capture-to-query paths are proven.
