# Wave 126 — Lossless WorkerIngest uint64 sequence and budget admission

## First-party production gRPC protocol change

The original Node WorkerIngest server accepted Protobuf `uint64` fields by calling `Number(subBatch.seq)` and `Number(subBatch.softBudgetMs)`. JavaScript cannot represent every `uint64` exactly, and comparing rounded sequence numbers is unsound at the message acknowledgement boundary. The original Protobuf contract explicitly says a soft budget of zero **or any value greater than 2^31−1** represents *unlimited*.

The production fix in `nodejs/src/ingestion/api/grpc-server.ts`:
- Compares wire `subBatch.seq` directly as **bigint** to `BigInt(stream.nextSeq)` and requires that the expected internal sequence remains `Number.isSafeInteger`, rejecting missing/regressed/unsafe positions with the existing `seq_mismatch` protocol failure **before** accepting or feeding a sub-batch.
- Represents any `softBudgetMs` greater than `2_147_483_647n` as the existing `0` sentinel for unlimited; converts only precisely representable smaller values with `Number()`. The maximum 64-bit unsigned value is therefore supported without rounding or using a timer beyond JavaScript's safe range.
- Rejects a malformed negative budget in a mock/programmatic request (Protobuf `uint64` naturally disallows it). Other WorkerIngest stream, routing, ACK, Kafka and ClickHouse contracts are unchanged.

The supplied first-party Jest tests gain **10 boundary cases**: three enormous `uint64` sequences fail without any pipeline feed or acknowledgement, six normal/boundary/large budgets are transmitted with exact intended semantics, and a negative injected budget fails closed.

## Actual executed validation (2026-10-26)

Using local Node26, real original Jest/ts-jest, source-provenance-guarded overlay into the temporary complete Node workspace, and frozen `pnpm` dependency closure available in the local store (2166 packages, zero downloads):
- `nodejs/src/ingestion/api/grpc-server.test.ts`: all old and 10 new protocol tests PASS.
- `grpc-message-converter.test.ts`, `kafka-message-converter.test.ts`, `grpc-stream-ingest-driver.test.ts`: PASS unchanged.
- **4/4 original Jest suites, 53/53 actual tests PASS, exit 0**. The reusable `tools/flind/qualify_node_ingestion_jest_wave125.py` now requires **at least 53** cases; source overlay was restored exactly in every run.
- Original Prettier project style check passed for both edited TypeScript files. Python syntax and Git whitespace checks PASS.
- No cloud resources, remote product environment, hosted service, publication or real data.

## Strict remaining gates

This fixes the actual Node **gRPC frame parser** and is tested directly in the full project's Jest environment. It does **not** qualify the running production `nodejs/src/ingestion` service connected to Rust, actual Kafka broker and durable production ClickHouse schema; nor tenant-authenticated query/dashboard, OAuth or the entire product build. The original `nodejs/tests/service-e2e/rust-ingestion-consumer.serial.test.ts` **performs database resets and is hardcoded to local shared service ports**; do not run it against the Mac's other running databases without explicit ephemeral sandbox isolation and preflight. Existing full TypeScript project checking was stopped at the disk safety floor and is not claimed PASS.

Issue #82 stays OPEN, release NO-GO, repo private, inherited GitHub Actions disabled, no paid provider, deployment or donor license removal.
