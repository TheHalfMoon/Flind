# Wave 127 — Fail-closed isolated Rust → production Node → Kafka → ClickHouse service E2E

## Why the original E2E suite was not safe to run on the user's Mac

The original `nodejs/tests/service-e2e/rust-ingestion-consumer.serial.test.ts` launches real Node ingestion API workers, runs a first-party Rust ingestion consumer, sends Kafka records, and validates actual ClickHouse product records, DLQ, and offsets. **It also calls `resetTestDatabase()` for PostgreSQL and ClickHouse at beforeEach/afterAll**. Previously it silently set shared `localhost:5432` PostgreSQL, `localhost:9092` Kafka, `localhost:6379` Redis and `localhost:8123` ClickHouse defaults, and forced fixed test database names. The Mac runs unrelated project databases: a direct invocation would risk destructive mutation.

Existing database-name guards protect against obvious non-test names but cannot prove an otherwise test-named database belongs to this Flind session. The test therefore must be explicitly admitted into a **user-owned, disposable, loopback-only** sandbox *before* Jest imports the Node configuration modules.

## Implemented product-test changes

- `nodejs/tests/service-e2e/rust-node-sandbox-admission.ts`: dependency-free, deterministic validation and expansion of `FLIND_E2E_*` options. Requires exact `FLIND_E2E_DESTRUCTIVE_ACK=I_OWN_THESE_DISPOSABLE_FLIND_TEST_DATABASES`, separate `127.0.0.1` loopback **nondefault** PostgreSQL (not 5432), Kafka (not 9092), Redis (not 6379), unique local ports, plus explicitly confirmed loopback ClickHouse and a high-entropy dedicated `flind_test_<12+lowercase-alphanumeric>` database name. PostgreSQL credentials must be supplied by the user through a base URL not selecting a database; derived URLs use dedicated `test_posthog`, `test_persons`, `test_behavioral_cohorts`, `test_cyclotron_node`. Refuses a direct Jest start where the full set of effective DB/Kafka/Redis variables was not prepared **before imports**.
- Original `rust-ingestion-consumer.serial.test.ts`: removes hardcoded shared service addresses and delegates to this validated sandbox. The `beforeAll` guard runs before **any suite call to destructive database reset**. All worker and Rust consumer subprocess environments derive from the same sandbox, including producer and group-inspector brokers.
- `nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs`: explicit wrapper that validates first, populates a deliberately **filtered child environment** before Jest imports any project modules, supports a dry-run without starting a service, then launches **the existing first-party serial Jest E2E**; no fake implementation. Refuses absent dependencies, starts only with at least 12GiB free, monitors a 10GiB free-disk floor and a bounded 6-minute run, and terminates the isolated Jest child process group on resource/timeout failures.
- The ClickHouse helper currently hardcodes HTTP port **8123**; this sandbox therefore requires exclusive ownership of that loopback port and a **unique, test-named disposable ClickHouse DB**. The admission guard does not automatically prove a port is unused/owned; the explicit acknowledgement remains material. Do NOT point this at another project's ClickHouse.

## Validation executed October 26, 2026

```sh
node --no-warnings --experimental-strip-types --test \
  tools/flind/test_rust_node_e2e_isolation_wave127.mjs
python3 -m unittest -q tools.flind.test_rust_node_e2e_sandbox_source_wave127
```

- **10/10 actual Node26 admission/CLI tests PASS**: missing ownership acknowledgement; shared/default/outbound Postgres/Kafka/Redis; invalid ClickHouse test database; collisions; correct derived test DB connection strings; direct-Jest refusal; wrapper refusal with missing permission; wrapper dry run successfully validates without starting or resetting services.
- **5/5 source guard tests PASS**: actual destructive E2E suites guard before reset, all child services receive explicit local endpoints, wrapper does not inherit ambient shell/cloud credentials, and no old shared default string remains.
- Node native syntax, Python syntax and Git whitespace checked. No calls made to reset Postgres/ClickHouse, no actual customer data or paid/cloud infrastructure; original service E2E itself remains **NOT EXECUTED / NOT QUALIFIED**.

## How to run *later in a real owned ephemeral sandbox*

Set `FLIND_E2E_DESTRUCTIVE_ACK`, `FLIND_E2E_POSTGRES_BASE_URL` (isolated 127.0.0.1 non-5432 port), `FLIND_E2E_KAFKA_BOOTSTRAP` (isolated non-9092), `FLIND_E2E_REDIS_URL` (isolated non-6379), `FLIND_E2E_CLICKHOUSE_HOST=127.0.0.1`, and a new unique `FLIND_E2E_CLICKHOUSE_DATABASE=flind_test_<12+lowercase-alphanumeric>`. Create and migrate the **disposable** PostgreSQL test databases and ClickHouse schema first; ensure exclusive ownership of all services, including ClickHouse 8123. Check:

```sh
node --no-warnings --experimental-strip-types \
  nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs --dry-run
```

Only after the full isolated stack exists should the same command be executed without `--dry-run`. The script does **not** create the backing databases or prove their ownership; it is an admission guard, not a replacement for live E2E.

## Release status

**Wave127 protects and enables safe isolation of the existing high-value full product E2E, but does not qualify it.** The running production Node WorkerIngest → durable ClickHouse → authenticated tenant query/dashboard chain still needs a real first-party end-to-end execution, alongside OAuth/PKCE, frontend/desktop builds, branding and release checks. Keep Issue #82 OPEN and release NO-GO, Flind private, inherited GitHub Actions disabled, no publication/deployment, no paid cloud, and legally required donor notices untouched.
