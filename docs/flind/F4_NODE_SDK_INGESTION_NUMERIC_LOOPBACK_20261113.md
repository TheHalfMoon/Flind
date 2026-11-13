# Flind Node SDK real-ingestion E2E: explicit numeric loopback

Status: the second real-service ingestion run **failed** on positive Node SDK
queryability; a revised direct-capture transport check awaits new CI.

## Original failure

Explicit `ingestion=true` on the original PR #68 head
`2ccfcdf07957cc479f62a210fbef91e1ec3061b5`:
https://github.com/TheHalfMoon/Flind/actions/runs/43354302818

This real-service run successfully built the frontend and local capture
services, migrated PostgreSQL/ClickHouse, and passed browser-SDK and direct
capture-to-query Playwright tests. The **Node SDK test failed at SDK host
validation**, before sending any event: the workflow intentionally used
`E2E_PROXY_URL=http://localhost:8010`, but the private SDK allows HTTP
only for a *numeric* loopback address. This is an appropriate security
restriction and must not be widened to support arbitrary hostnames.

## Evidence from second run

The retry at `40f6e0f66650eec3a351ab7c19ff12b7f83a1200`,
https://github.com/TheHalfMoon/Flind/actions/runs/43360778574,
passed browser SDK and direct capture ingestion but failed the positive
Node SDK count after 90 seconds. SDK host validation no longer failed.
This means a successful local HTTP transport has **not** been established;
there is insufficient evidence to say whether the dev proxy rejected the
numeric-host request, or the SDK payload failed another ingestion check.

## Next repair

- Keep browser and direct capture coverage through the existing dev proxy.
- Validate numeric loopback and absence of credentials/query/fragment.
  The SDK's secure-origin policy remains untouched.
- Send the Node SDK's batch request to the **actual Rust capture service**
  at `http://127.0.0.1:3307`, the ephemeral ingestion workflow's already
  health-checked local capture port. The dev proxy accepts a separately
  configured host and is still covered by the other two Playwright tests.
- Inject a test-only fail-closed fetch wrapper to reject any non-local
  destination or unexpected `/batch/` path **before sending**. Record only
  HTTP statuses, and assert an actual successful capture response and zero
  SDK error events before attempting positive and cross-tenant queries.
- Preserve distinct GitHub Actions concurrency groups for normal browser
  E2E and explicitly opted-in full-service ingestion E2E; otherwise an
  optional test may cancel ordinary PR checks.

This deliberately avoids assuming that an SDK flush implies successful
capture. It also does not prove an owned HTTPS production reverse proxy.

## Qualification

The dependency-free Node source-contract suite must pass, but is **not**
a substitute for the real three-test suite. After this repair, the
`flind-e2e.yml` workflow with `workflow_dispatch ingestion=true`
must pass *all three* browser SDK, direct capture and Node SDK tests,
including queryable events in the originating tenant and zero results
in a distinct tenant. Exact-head ordinary browser E2E, rename ratchet
and real migrations are required before merging.

No broader trust of `localhost`, no credentials, no production traffic,
no remote collector, no package publication, and no release/tag without
explicit `GREEN LIGHT FLIND`.
