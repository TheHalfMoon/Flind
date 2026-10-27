# Flind Wave 185 — Real original Node gRPC precision and sanitization, offline

## Qualification result — October 27, 2026

**PASS: 32/32 actual Node26 runtime checks** against three original, private, **Git-blob-verified** first-party Flind TypeScript modules:

1. `nodejs/src/ingestion/api/grpc-message-converter.ts` — source Git SHA1 `c507eb01e27354fa88144c959afa903479288ab5`.
2. `nodejs/src/ingestion/api/kafka-message-converter.ts` — source Git SHA1 `1a572256bc5616afd84919e46b0b39119e99fb80`.
3. `nodejs/src/ingestion/api/grpc-error-sanitizer.ts` — source Git SHA1 `899d7e608dc2915c630c0bf40feaae8aff0c95f0`.

These source blob IDs were checked against pinned private Flind Git source `1905e9afb0f25f2685f042485b59f4c433403ffe` and the GitHub private main at the time of qualification. This **attests these three modules only**, not a freshly rebuilt entire Node server.

`tools/flind/verify_original_grpc_boundary_wave185.mjs` directly imports the *unmodified original TypeScript source*, with Node26 `--experimental-strip-types` and no runtime third-party npm dependencies; `tools/flind/qualify_original_node_grpc_primitives_wave185.py` verifies the exact Git-tracked modules against SHA1 content, refuses source drift/symlinks, launches that bounded real Node process with closed stdin and bounded output, validates all results and never promotes production server qualification.

### 32 original-source runtime assertions

- Kafka gRPC protobuf **bigint offset and timestamp** conversion preserving exactly representable values (0, -1, MAX_SAFE_INTEGER, MIN_SAFE_INTEGER), rejecting unrepresentable ±2^53 and signed 64-bit extrema with a `RangeError` before offset acknowledgement or ordering corruption.
- Real **gRPC → serialized Kafka → original deserializer** roundtrip preserves topic, partition, offset, synthetic JSON event UUID, key, UTF-8 value, byte size and headers.
- Difference between a true **Kafka tombstone** (`value=null`) and zero-length payload (`value=''`) is preserved, as is empty key/header and Arabic Unicode Kafka key.
- Original `safeIngestFailureMessage` leaks **none** of the synthetic private diagnostic contents for arbitrary error objects, `Error` instances, null/undefined, or a malicious `toString`, returning only the fixed generic `ingest pipeline failed`.
- Explicit output flags `production_grpc_server_qualified=false`, `production_node_grpc_server_qualified=false`, `production_node_worker_qualified=false`, `real_rust_to_production_node_qualified=false`, `durable_clickhouse_qualified=false`, `authenticated_tenant_isolation_qualified=false`, `release_qualified=false`.

**Actual standalone Node26 runtime exit 0, 32/32 passed.** **8/8 Python guard tests PASS** (`-W error::ResourceWarning`) including Git source drift and unsafe symlink refusal, absent Node, wrong assertion counts, forged production server/release flags, and an actual end-to-end original-source Node execution. A negative test initially exposed an omission where the new qualifier might accept a forged `production_node_grpc_server_qualified=true` flag; this was fixed, the Node receipt explicitly marks it false, and **all eight tests passed on the exact final proposed source**.

### Why the full production gRPC worker still cannot run locally

The previously used disposable full repo checkout `/private/tmp/flind-wave76-frontend` retains original `nodejs/src/ingestion/api/grpc-server.ts` and test files, but its pnpm links reference missing `<checkout>/node_modules/.pnpm`; running Jest exits **before loading the server tests** with a `Cannot find module .../.pnpm/.../jest/bin/jest.js` error.

The Mac has a large user-owned pnpm store (~6.4GiB v3 content and ~4.0GiB v11 content), but an **isolated scratch-only** attempt to resolve just four core package dependencies (`@bufbuild/protobuf@2.11.0`, `@connectrpc/connect@2.1.1`, `@connectrpc/connect-node@2.1.1`, `prom-client@14.2.0`) using `pnpm install --offline --ignore-scripts` failed with **`ERR_PNPM_NO_OFFLINE_META`**, missing the @connectrpc/connect-node package metadata. Nothing was downloaded and no original checkout/project package files were overwritten. Mac had ~4.5GiB free at the test start; no unrestricted install or heavy downloads were attempted.

**These primitive tests do NOT instantiate `WorkerIngestServer` or exercise an actual gRPC wire session, production Node worker, native Rust consumer-to-production Node integration, ClickHouse durable persistence, API/authentication or SDK/dashboard.** Wave184's nine native Rust Kafka/gRPC tests use the **original test WorkerIngest server**, separately qualified.

**Issues #82 and #5 remain OPEN, release NO-GO.** Repo PRIVATE, inherited GitHub Actions disabled, no release/deploy/publication or paid inference/services, real customer records, unapproved downloads, and mandatory third-party legal attribution preserved.
