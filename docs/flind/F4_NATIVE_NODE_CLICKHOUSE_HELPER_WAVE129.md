# Wave 129 — Real first-party Node ClickHouse helper against private ClickHouse 25.12.7.21

## What advanced over Wave128

Wave128 proved the actual dependency-free `clickhouseTestHttpOrigin` function, imported by the project's original ClickHouse test helper, could connect to a genuine temporary ClickHouse server on a nondefault loopback port. But attempts to run the **complete original Node helper** were blocked before test execution: the full helper's transitive event-utils import required native `re2@1.22.1`, left unbuilt by our safe original `pnpm install --ignore-scripts` command.

Wave129 built the pinned first-party dependency locally and ran the **actual original `Clickhouse.create()` / `client.query()` implementation** against genuine isolated ClickHouse with first-party Jest.

## Native dependency qualification (no paid/cloud resources)

The Mac has installed Node26, Node24 and Node22. Node22 binary was not usable because its Homebrew dynamic `libsimdjson.31.dylib` dependency was missing. Native `re2@1.22.1` compile attempts under default Node26 failed with genuine **V8/NAN API incompatibility** (no `PropertyCallbackInfo<void>::This()`). Initial manual compiler attempts also exposed missing macOS libc++ SDK and libuv include paths.

A local, bounded, offline `node-gyp` rebuild using **already installed Node24.15.0**, the native macOS SDK, local Node/libuv headers, and **two compiler jobs** succeeded (**exit 0**, ~30 seconds) with no downloads or global Node version change. The resulting private scratch-only ARM64 addon `re2.node` is importable with Node24 and successfully evaluates a real RE2 regex. This remains a **temporary local qualification**; no binary is committed to the repo, and source legal attributions are unchanged.

`tools/flind/bootstrap_native_re2_node24_wave129.py` records this same bounded setup as a reproducible, idempotent helper. It skips compilation if the pinned Node24 ABI binding is already working, otherwise compiles with a 100-second ceiling and 10.5 GB free-disk reserve, strictly from the local pinned source/Node headers. No `brew`/npm cloud install or publication.

## Real native Node helper + ClickHouse test

`nodejs/tests/helpers/clickhouse-real-port-wave129.test.ts` is a real original-project Jest test. It calls:
```ts
const client = Clickhouse.create()
const database = await client.query('SELECT currentDatabase() AS name')
const rows = await client.query('SELECT count() AS count, sum(value) AS sum FROM flind_private_probe')
client.close()
```
There is **no mocked ClickHouse client, no mocked RE2 and no fake SQL result**.

`tools/flind/qualify_node_clickhouse_helper_wave129.py` starts actual supported local ClickHouse25.12.7.21 in a private temporary working directory at an ephemeral **127.0.0.1 nondefault port**, creates a unique `flind_test_...` database and a Memory table with synthetic values (10,20,30), overlays current Flind main helper and Jest test sources into the original complete pinned scratch checkout, and runs the actual project's Jest/ts-jest under Node24. It then restores every test overlay byte-for-byte and disposes of the owned ClickHouse process and temporary files.

The first run initially failed because the original Jest setup defaulted `CLICKHOUSE_DATABASE=posthog_test` before running this custom isolated case; fixed **only the test fixture** to set the owned temporary database before constructing the original Clickhouse helper. No production code workaround was needed.

**Executed 2026-10-26:** `python3 -m tools.flind.qualify_node_clickhouse_helper_wave129` **exit 0**. Jest **1/1 PASS**, real database verified, **three rows and sum=60** from genuine ClickHouse; `scratch_source_restored=true`. Independently repeated both the RE2 import qualification and live Node/Jest/ClickHouse helper successfully, retaining ~13 GiB Mac free disk.

## Reproduction

```sh
python3 -m tools.flind.bootstrap_native_re2_node24_wave129
python3 -m tools.flind.qualify_node_clickhouse_helper_wave129
python3 -m unittest -q tools.flind.test_node_clickhouse_helper_wave129
```

If the pinned scratch Node modules or a supported local ClickHouse/Node24 are unavailable, the scripts fail closed instead of touching installed system services.

## Exact release boundary

**Qualified:** pinned local RE2 native library under Node24; real original-project Jest invoking the original Flind Node ClickHouse test-helper's `Clickhouse.create()` and `query()`, with actual private ClickHouse server SQL readback.

**Not qualified:** running full production Node ingestion API worker process, running first-party Rust consumer against that worker, real Kafka event persistence into **production** ClickHouse event schemas/materialized views, tenant-authenticated read API, Dashboard/browser, OAuth/PKCE or full product build. The latest complete original service E2E suite is still **unexecuted** because it requires disposable migrated PostgreSQL and ClickHouse schemas, Kafka, Redis and production Node native dependencies. Keep Issue #82 OPEN, release NO-GO, private repo, inherited GitHub Actions disabled, no deploy/publication, paid cloud or removal of mandatory donor attributions.
