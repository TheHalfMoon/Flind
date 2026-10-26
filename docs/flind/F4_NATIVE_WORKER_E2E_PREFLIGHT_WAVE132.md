# Wave 132 — Native Node worker preflight before destructive service E2E

## Goal
The original first-party Rust → Node ingestion API → Kafka → ClickHouse Jest suite must not enter its database-reset fixture if the Node worker's actual runtime cannot load its required native packages. A lockfile install with `--ignore-scripts` can leave `re2` and `node-rdkafka` missing their native bindings; `tsx` is also required to launch real worker subprocesses. Merely finding the Jest executable does not qualify these runtime dependencies.

## Implementation
- Added dependency-free `nodejs/tests/service-e2e/native-runtime-preflight.mjs`: check a first-party Jest entrypoint exists, then spawn a short, isolated child using `node` resolved from the **same PATH** as the eventual Jest process.
- Child attempts actual `require('node-rdkafka')`, `require('re2')` and `require.resolve('tsx')`. On timeout, crash, bad ABI or missing module, abort with a generic message. Child stdio is discarded; never output connection environment or package error stack containing private paths.
- The existing `run-rust-node-sandbox-e2e.mjs` invokes this check **after** exact disposable sandbox admission, explicit local Jest prerequisite and disk checks, but **before** spawning the destructive Jest suite. Its existing `--dry-run` remains zero-side-effect and checks admission only.

## Actual Mac evidence (2026-10-26)
- Loaded the exact GitHub branch source files into a temporary isolated proof directory, ran the native prerequisite unit cases with installed Node24: **PASS, exit 0**. Fake installed packages prove successful admission and synthetic missing/crashing dependencies prove sanitized fail-closed logic. These fake packages are unit-test fixtures, *not* a claim of real worker readiness.
- Ran the real updated runner with four dummy nondefault `127.0.0.1` endpoints and the exact disposable acknowledgement. `--dry-run` **PASS** with no services started. Repeated normal entrypoint with only a placeholder Jest file and no native runtime: **REFUSED, exit 2** before Jest launch or any database reset.
- Attempted a real `pnpm --offline` frozen install in an independent clean Git worktree: refused because tarballs are absent from the local store. Then attempted a bounded public npm registry install (free, `--ignore-scripts`), but stopped it to protect the Mac's 8 GiB RAM and disk reserve. **No first-party worker boot has been qualified.** Temporary worktree is disposable; repository main unchanged by dependency installation.

## Next qualification gates
Install a supported frozen Node worker dependency graph in a resource-safe test environment; compile native modules against the actual Node ABI, boot isolated real Node workers, then run authorized disposable PostgreSQL/Redis/Kafka/ClickHouse end-to-end fixtures and authenticated API/Dashboard reads. Keep release blocker #82 open and release **NO-GO**. Preserve repository privacy, disabled inherited Actions, notices and attribution; no deployment, publication or paid services.
