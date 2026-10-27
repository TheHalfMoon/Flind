# Flind Wave 186 — Real first-party WorkerIngestServer over HTTP/2/gRPC

## Verified 27 October 2026 — 20/20 real wire assertions; 9/9 harness guards

**PASS:** the actual first-party \`WorkerIngestServer\` from \`nodejs/src/ingestion/api/grpc-server.ts\` was started as a Node26 HTTP/2 server. A real \`@connectrpc/connect-node\` **gRPC** client (\`createGrpcTransport\`, not an in-process \`ingestStream()\` call) communicated with that server using Flind's actual generated Protobuf \`WorkerIngest\` descriptors. A synthetic \`StreamIngestDriver\` backed its batch processing; the production driver/pipeline was **not run**.

### Original source / dependencies

Eight exact Git blob-verified original Flind modules from the pinned private source commit \`1905e9afb0f25f2685f042485b59f4c433403ffe\`, also matched against the private current \`main\` tracked blob IDs at qualification time:

| File | SHA-1 Git blob |
|---|---|
| \`nodejs/src/ingestion/api/grpc-server.ts\` | \`5a32b131056bb1e7f10e8bca824c149097d2d563\` |
| \`nodejs/src/ingestion/api/grpc-message-converter.ts\` | \`c507eb01e27354fa88144c959afa903479288ab5\` |
| \`nodejs/src/ingestion/api/grpc-error-sanitizer.ts\` | \`899d7e608dc2915c630c0bf40feaae8aff0c95f0\` |
| \`nodejs/src/ingestion/api/batch-metrics.ts\` | \`b9f96bb05d5360505575964f8c9520968c72e6df\` |
| \`nodejs/src/ingestion/api/feed-order-sentinel.ts\` | \`2a48963dec62a60e3bc5e45243e1693f245deb49\` |
| \`nodejs/src/ingestion/api/types.ts\` | \`b9475f0a3803f9e173e9dcd8ac01f40c75fce9a3\` |
| \`nodejs/src/ingestion/framework/batch-budget.ts\` | \`2b3a1881ebecec2ec5cc07b856e30618a21bd513\` |
| \`nodejs/src/common/generated/ingestion-worker/ingestion/worker/v1/worker_pb.ts\` | \`c9d57314ca63412ff5c15d2c6d3b8e900ce774a7\` |

Five precisely pinned free npm packages were installed **only in the marker-owned test scratch** (no pre-existing Flind checkout changes): \`@bufbuild/protobuf@2.11.0\`, \`@connectrpc/connect@2.1.1\`, \`@connectrpc/connect-node@2.1.1\`, \`prom-client@14.2.0\`, and \`esbuild@0.25.12\`. \`npm install --ignore-scripts --no-audit --no-fund --save-exact\` completed successfully. The existing original first-party \`patches/@connectrpc__connect-node@2.1.1.patch\` was applied to both CJS and ESM HTTP/2 session-manager files inside **that scratch-only npm dependency**. The bounded verifier checks exact versions and patch presence before running.

A **clearly identified test-only no-op logger shim** replaced Flind's original logger to avoid pulling unrelated application bootstrap dependencies. The batch driver is a **synthetic test double** that accepts messages and resolves settled completions. Every other runtime Flind module listed above was copied byte-for-byte from Git, with SHA-verified source. Esbuild is used only to bundle the original TypeScript modules and resolve Flind's \`~\` import aliases, with actual Connect/Protobuf/prom-client dependencies remaining external packages.

### 20 actual gRPC wire assertions

The standalone fixture \`tools/flind/verify_actual_node_grpc_http2_wire_wave186.mjs\` tests real server start and ephemeral port, HTTP/2 gRPC frame exchange, immediate ready response, valid sub-batch \`seq=1\` accepted count/status, source Kafka offset preservation, sequence-gap rejection with \`Code.FailedPrecondition\`, rejection of an unsafe bigint Kafka offset before the fake driver can feed it, acknowledgement of an empty batch without feeding the fake driver, and duplicate hello rejection. It closes the server after these checks.

- **20/20 actual gRPC-wire assertions PASS**; standalone Node test completed with exit 0 in about 5.4 seconds including HTTP/2 session cleanup.
- \`tools/flind/qualify_actual_node_grpc_http2_wire_wave186.py\` validates marker-owned \`/private/tmp\` scratch, 3GiB free disk reserve, exact Git source blobs, five exact npm versions, first-party Connect patch application, two approved in-repo JS fixtures, and actual Node test completion, without making network calls or installing any packages itself. It never promotes the test worker to production.
- **Source-attested qualification script exit 0**, reported \`real_first_party_http2_grpc_worker_server_qualified=true\` and \`synthetic_wire_assertions_passed=20\` (elapsed approximately 21.2 seconds, mostly exact offline Git blob reads).
- **9/9 Python guard tests PASS** with \`-W error::ResourceWarning\`, covering source inventory, exact success count, forged production/release receipts, unmarked scratch, wrong owner marker, missing dependencies/Connect patch and source drift, plus **a second full real-node end-to-end wire run**.

### Reproduction (free, local, scratch only)

Create a fresh, marker-owned \`/private/tmp/flind-wave186-grpc-core\` scratch directory. Install exactly the five versions above with free npm, scripts/audit/funding hooks disabled. Apply the existing Flind Connect patch **to the scratch-installed @connectrpc/connect-node package**, not the original repository. Then run:

\`\`\`bash
python tools/flind/qualify_actual_node_grpc_http2_wire_wave186.py \
  --reference /path/to/private/source-checkout \
  --scratch /private/tmp/flind-wave186-grpc-core \
  --scripts-root /path/to/Flind \
  --json
\`\`\`

The scratch must contain the marker file \`.flind-wave186-owner\` with exactly \`FLIND_WAVE186_OWNED_GRPC_CORE_V1\` followed by a newline. The verifier **does not silently download dependencies**; it fails closed if a required version, original source blob, mark or patch is missing. It uses original Git contents, not the older local checkout's stale Node sources. The verifier's builder and test harness are tracked under \`tools/flind/\`.

### What has *not* been qualified

- The Node server uses a **test-only synthetic processing driver and no-op diagnostic logger**; no actual first-party production \`BatchingPipeline\`, durable batch side effects, real Kafka commit frontier or Node process production bootstrap ran.
- No live original Rust ingestion-consumer → this actual production Node server gRPC session, nor first-party worker-to-ClickHouse persistent Kafka/MergeTree storage.
- No tenant-authenticated data path, real SDK capture→API→Dashboard browser/desktop E2E, full PostgreSQL migrations and recovery, OAuth/PKCE/JWKS or final Flind identity/legally required notices audit.
- Real gRPC traffic was synthetic and client-targeted to \`127.0.0.1\`; the unmodified first-party server creates an ephemeral listener via \`listen(0)\` without binding a specific hostname. **Do not treat this harness as proof of a network-restricted production deployment**.

**Issue #82 and #5 remain OPEN, Release NO-GO.** GitHub repo stays PRIVATE, inherited Actions disabled; no deployment, publishing, paid compute/models or customer records. Legally required third-party notices must be retained.
