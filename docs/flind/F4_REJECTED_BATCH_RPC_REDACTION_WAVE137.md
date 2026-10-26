# Wave 137 — Sanitize WorkerIngest rejected-batch ACK and RPC errors

## Production defect

Wave136 sanitized fatal ingestion errors, but the first-party `WorkerIngestServer.runReader` non-capacity rejection branch still directly exposed the pipeline's `FeedResult.reason` in **two distinct network surfaces**:

1. `SubBatchAck.status=FAILED` with `error=result.reason`
2. The stream's `ConnectError(Code.Internal)` interpolating `result.reason`

Although the current `before_batch_failed` hook often returns a predictable reason, `FeedResult` permits arbitrary strings and other code paths or future hooks can supply credentials, internal paths or event metadata.

## Change

Both outgoing message fields now use the established `safeIngestFailureMessage(result.reason)` helper, which never inspects or stringifies the internal reason, and returns the generic `ingest pipeline failed`. Crucially, the sub-batch still produces `FAILED` and throws `Code.Internal`; this does not transform a rejected batch into a successful ACK or conceal the failure from Rust consumer retry semantics. Existing internal error handling and metric counting remain otherwise unchanged.

Strengthened the **original first-party `grpc-server.test.ts`** rejection test: it feeds `hook failed: PRIVATE_KAFKA_TOKEN`, asserts a `FAILED` ACK with generic error, asserts `Code.Internal` with retained batch sequence context, and forbids secret exposure in either response. This full Jest test was **not run** because the original native Node dependency workspace is not release-qualified on the connected Mac.

## Executed proof

The GitHub branch files were fetched and inspected on the connected Mac and actual pure TypeScript sanitizer was executed with Node24 `--experimental-strip-types` in a private temporary proof directory.

`tools/flind/test_wave137_rejected_batch_redaction.mjs`: **PASS, exit 0**. Tested secret-bearing token/database URL/event string/Error/throwing-`toString()` inputs; verified that the production rejection code uses `publicReason` for both ACK and ConnectError and retains `FAILED` metrics/status; verified the original Jest test includes both redaction assertions. Did not use an external service, mutate any database or claim full server runtime success.

## Remaining blockers

Release Issue #82 remains OPEN: full original WorkerIngest Jest on a supported ABI, true Rust→production Node→Kafka→ClickHouse durability, authenticated query readback, tenant isolation, Django/browser E2E and security qualification have not passed together. Repo PRIVATE, Actions disabled, no publication/deployment/paid resources; retain legal attribution.
