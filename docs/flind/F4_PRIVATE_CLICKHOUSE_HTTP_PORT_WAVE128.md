# Wave 128 — Private ClickHouse port for safe full-service E2E, with real HTTP proof

## The cross-project ClickHouse isolation gap

Wave127 protected the original first-party Rust→Node→Kafka→ClickHouse service E2E with a unique test database, dedicated PostgreSQL/Kafka/Redis ports and explicit ownership acknowledgement, but the original ClickHouse helper **still hardcoded `127.0.0.1:8123`** for both API reads and its health probe. That was incompatible with a fully private Mac test stack, where other projects might use ClickHouse's default service port.

Wave128 makes **a nondefault, distinct ClickHouse HTTP port mandatory** for the destructive service-E2E sandbox. It does not change product production Kafka or gRPC protocol or ClickHouse schema.

## Files and behavior

- `nodejs/tests/service-e2e/rust-node-sandbox-admission.ts`: requires `FLIND_E2E_CLICKHOUSE_HTTP_PORT`, a valid nondefault, dedicated port. Rejects remote ClickHouse hosts, port collisions with isolated PostgreSQL/Kafka/Redis and **all common shared ports 5432/9092/6379/8123**. Projects keep their own database instances untouched. The approved ClickHouse HTTP port is passed as `CLICKHOUSE_HTTP_PORT` to the real E2E parent and spawned Node workers.
- `nodejs/tests/helpers/clickhouse-http-endpoint.ts`: dependency-free endpoint function. Uses `CLICKHOUSE_HOST` and `CLICKHOUSE_HTTP_PORT` to construct the ClickHouse origin, validating host and port. Maintains backwards compatibility for other original tests using localhost:8123 when not within the new strict sandbox.
- `nodejs/tests/helpers/clickhouse.ts`: actual first-party Clickhouse helper imports and reuses the exact endpoint function for both **client SQL connection** and **`/ping` health check** (no remaining hardcoded health target). This refactoring does not change its response parsing or database-query semantics.
- Original Wave127 Node/Python sandbox tests expanded to check ClickHouse nondefault port and safe propagation. New Node unit tests verify malformed hosts/ports fail closed and the same helper selector is used by client and health.

## Executed evidence on the user's Mac — October 26, 2026

**Actual local ClickHouse 25.12.7.21 executable** from the previously qualified free binary started as an isolated loopback-only process with memory limits and a temporary data directory. It listened on a newly selected nondefault HTTP port (never shared localhost:8123). It created a one-off `flind_test_isolatedwave128q9a1` database and temporary Memory-engine table with three synthetic UInt32 values (10, 20, 30).

A **real Node26 process executing the exact `clickhouseTestHttpOrigin` function imported by the original project helper** then sent HTTP SQL queries to that specific private ClickHouse instance. The readback verified `currentDatabase()` matched the unique test DB and obtained **three rows with sum 60**, exit code **0**. The owned ClickHouse process was stopped by the existing bounded helper's `finally`, and its temp data directory disposed. No other service, DB, customer data, or paid cloud involved.

To reproduce:
```sh
python3 -m tools.flind.qualify_node_clickhouse_private_port_wave128
python3 -m unittest -q \
    tools.flind.test_node_clickhouse_private_port_wave128 \
    tools.flind.test_rust_node_e2e_sandbox_source_wave127
node --no-warnings --experimental-strip-types --test \
    tools/flind/test_clickhouse_http_origin_wave128.mjs \
    tools/flind/test_rust_node_e2e_isolation_wave127.mjs
```

**Live Node→real isolated ClickHouse SQL qualified; 10/10 Python tests PASS (including a second real live service run), and 16/16 Node isolation/endpoint unit tests PASS.** Git whitespace and syntax checks PASS. The Mac retained ~13GiB free.

## Important blocked test

We also attempted to import and exercise the original **full `Clickhouse` test helper** in first-party Jest against the same isolated server. It failed at **module import**, before executing a test or any SQL, because the private frozen-lockfile `pnpm --ignore-scripts` installation leaves **native `re2` bindings unbuilt**, pulled indirectly by event utility imports. We did **not** mock `re2` and did not claim this failing full helper test passed. The successful Node HTTP test uses the exact dependency-free **endpoint selector now imported by the original helper**, but does not boot the full helper.

**Full Rust consumer→production Node workers→ClickHouse persistence and the test helper's real native dependencies remain unqualified.** Creating a fully provisioned disposable ClickHouse/Postgres schema (and a Node native dependency build) is a separate release gate. Keep Issue #82 OPEN, release NO-GO, repo private, inherited GitHub Actions disabled, no publication/deployment/paid resources, mandatory donor attribution preserved.
