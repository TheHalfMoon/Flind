# Wave 125 — Real first-party Node WorkerIngest Jest qualification (43 tests)

## Removed the Node-test dependency blocker at zero cloud cost

Previous Wave115 and Wave124 repairs to the first-party TypeScript Kafka and WorkerIngest gRPC adapters were tested by executing their production TypeScript functions directly under local Node26. The original project Jest suites had remained **unqualified**, because the full locked Node workspace dependency tree was absent in the existing scratch checkout.

On the Mac, ran a **guarded, free, registry-backed pnpm installation** into the **older private temporary full-source test checkout only**:

```sh
pnpm --filter '@flind/nodejs...' install \
  --frozen-lockfile --ignore-scripts --prefer-offline \
  --reporter append-only
```

- **Install EXIT 0** in 16.9 seconds using pnpm 11.28.5 and the original frozen lockfile; 2166 packages resolved and added, 1298 recovered from local cache and 828 fetched from the public npm registry. This is free dependency download, **not** a paid cloud provider or an application deployment.
- `--ignore-scripts` intentionally blocked package postinstall/build scripts; the full product build/runtime therefore remains **unqualified**.
- A supervising process enforced a >=10.5GiB disk reserve and 120s timeout. The Mac retained ~11.4GiB free. No project root lockfile or user source files were changed by the install.

## First-party Jest execution

Temporarily overlaid the **actual latest Flind main** source files into the older, full Git-backed scratch checkout (including the Wave115/124 converters and unchanged server/stream driver). Every replacement was guarded against preexisting user modifications, then restored byte-for-byte on exit.

Executed **real pnpm-installed Jest 30 + ts-jest** under `nodejs/jest.config.js`, not Node native tests or a simplified reimplementation:

- `src/ingestion/api/kafka-message-converter.test.ts` — first-party Kafka values, key/header/tombstone semantics, including Wave115.
- `src/ingestion/api/grpc-message-converter.test.ts` — Wave124 Protobuf int64 safe/unsafe conversion and field preservation.
- `src/ingestion/api/grpc-server.test.ts` — actual gRPC WorkerIngest server protocol, admission, ordering, ACK, and simulated failure behavior.
- `src/servers/grpc-stream-ingest-driver.test.ts` — actual Node ingestion driver dispositions and budget propagation.

Initially qualified **19/19 tests across both converter files**, then **24/24 across gRPC server/driver**, then reran all four together via a reusable harness:

```sh
python3 -m tools.flind.qualify_node_ingestion_jest_wave125
python3 -m unittest -q tools.flind.test_node_ingestion_jest_wave125
```

**Final independent combined first-party Jest run: 4/4 suites PASS, 43/43 tests PASS, exit 0**. The native test process completed in approximately 2 seconds. `temporary_checkout_sources_restored=true`. The existing Jest suite emitted warning/error logs for **intentionally invalid protocol frames and simulated pipeline failures**, but the Jest exit code and all test assertions passed.

The Python harness is bounded (100s/10GiB disk floor), exact four Jest file paths, requires previously available local dependencies, runs no install itself, checks every suite and at least 43 original tests, preserves scratch sources, and never executes a release/publish command. **5/5 Python harness/refusal tests PASS**, including a second actual combined Jest run.

## Remaining scope

**Qualified:** original real Node Jest suites for the first-party Kafka and gRPC converters, WorkerIngest stream server protocol, and gRPC stream-to-pipeline driver. This is substantially stronger than running only extracted functions.

**Not qualified:** a continuously running production `nodejs/src/ingestion` worker with its real external services, actual Rust consumer→**production Node** gRPC event flow, production durable ClickHouse `events` storage and app-specific transformations, real tenant/authenticated API, browser Dashboard, OAuth/PKCE and full frontend/desktop builds. Installing deps with `--ignore-scripts` also does not establish that any native extensions work.

Keep Issue #82 OPEN and Flind release NO-GO. Repository remains private and inherited Actions disabled; no publication/deployment, paid resources or removal of required donor legal attribution.
