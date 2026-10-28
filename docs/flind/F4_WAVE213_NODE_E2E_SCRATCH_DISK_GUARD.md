# Flind Wave 213 - Local Node/Rust E2E scratch volume gate

## Original blocker

The original `nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs` checked
`/tmp` for 12 GiB entry and 10 GiB ongoing free-space reserves. On WSL,
`/tmp` is a 3.9 GiB tmpfs but the actual Flind checkout has over 900 GiB
free. The runner therefore rejected the test before any native dependencies
were checked. This was a false storage blocker, not a passing joined E2E.

## Correction

- Create an isolated random scratch directory alongside the Flind checkout on
  the real checkout filesystem, not an inherited or arbitrary `TMPDIR`.
- Require 12 GiB before running and 10 GiB throughout the test on that volume.
- Point child Jest and workers at the exact owned scratch via `TMPDIR`.
- Delete only a scratch directory carrying the exclusive expected owner marker;
  a symlink or mismatched marker fails closed.
- Clean the owned directory on both native preflight failure and Jest close.
- Retain all existing isolation gates against unsafe database reset endpoints.

## Executed verification

Windows/WSL Node 24.15.0 (the project requires Node >=24 <25):

- `node --test nodejs/tests/service-e2e/local-scratch.test.mjs`:
  **4/4 PASS**, covering owned cleanup, marker tampering, symlink and low-disk.
- `node --check nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs`: PASS.
- Service runner `--dry-run` with no sandbox: expected refusal (exit 2).
- Service runner `--dry-run` with explicitly synthetic loopback endpoints:
  admitted (exit 0), no services started and no database reset.
- Full runner preflight with synthetic endpoints: expected refusal (exit 2)
  because the first-party frozen-lockfile Jest dependencies are absent.
- Git staged diff whitespace validation: PASS.

## Limitations

The original `rust-ingestion-consumer.serial.test.ts` Jest service suite
has **not** executed. First-party Jest, native `node-rdkafka`, `re2`, `tsx`,
production Node joined analytics, isolated PostgreSQL/Redis/ClickHouse, durable
ClickHouse persistence and SDK/browser E2E remain unqualified.
Wave 212 separately tested the real Rust consumer with a mock gRPC worker.

**Release NO-GO**. Repo PRIVATE, Actions disabled, no deployment, publication,
production data, paid services, or claims of full end-to-end qualification.
