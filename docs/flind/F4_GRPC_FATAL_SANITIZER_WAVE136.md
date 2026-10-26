# Wave 136 — Do not forward internal WorkerIngest failures over gRPC

## Actual production defect

The first-party `nodejs/src/ingestion/api/grpc-server.ts` forwarded `error.message` to all streaming consumers in `fatal()`, using `new ConnectError(`ingest pipeline failed: ${error.message}`, Code.Internal)`. Its outer stream-reader catch also constructed `new ConnectError(String(error), Code.Internal)` for unexpected errors. A downstream driver exception may include tokens, endpoint details, file paths or private record metadata. Those diagnostic details should remain internal, not cross the WorkerIngest RPC boundary.

## Fix

- Added a dependency-free `safeIngestFailureMessage(cause)` which deliberately discards the cause and returns `ingest pipeline failed` for externally sent unexpected/internal failures.
- Both the global `fatal()` stream failure and the reader's unexpected-error conversion now use this sanitized public message.
- The original `onFatal(error)` owner callback still receives the complete `Error` object for internal shutdown/recovery/reporting. Existing explicit protocol rejection codes and client-visible argument validation are unchanged.
- The existing first-party `grpc-server.test.ts` fatal case now injects a synthetic `SECRET_INTERNAL_KEY`, asserts the gRPC-visible error excludes the secret, and asserts the internal `onFatal` callback still receives the full error. This Jest test was **added but not run in this wave** because the full pinned Node native dependency graph remains incomplete on the user's Mac.

## Executed evidence

Fetched the exact GitHub branch into a temporary isolated source-proof directory on the Mac. Ran `node --experimental-strip-types tools/flind/test_grpc_error_sanitizer_wave136.mjs` with installed Node 24, **PASS exit 0**:

- Actual pure TypeScript function returns a constant safe message for Error, string, null/undefined and an object whose `toString()` itself throws a secret-bearing error.
- Checks both production `new ConnectError(... Code.Internal)` sites use the sanitizer rather than interpolating private error details.
- Checks the original tracked Jest suite includes the new secret-redaction and retained `onFatal` assertions.

## Release boundary

This is a scoped, actual production-code privacy/correctness fix with direct sanitizer execution and source wiring evidence. Full first-party WorkerIngest Jest, native linked production Node worker runtime, real Kafka/ClickHouse durability, Django tenant authorization and browser/Dashboard E2E **remain unqualified**. Issue #82 stays OPEN, release NO-GO. Repo PRIVATE, inherited Actions disabled, no paid services, deployment, publishing or removal of mandatory donor notices.
