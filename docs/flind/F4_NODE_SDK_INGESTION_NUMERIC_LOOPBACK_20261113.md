# Flind Node SDK real-ingestion E2E: explicit numeric loopback

Status: regression repair **pending new exact-head real-service CI**.

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

## Repair

- Keep browser/direct capture using their existing local proxy setting.
- On the Node SDK Playwright test, first validate that the configured
  proxy is truly HTTP loopback with no credentials, query or fragment.
- Set the validated URL's hostname to **127.0.0.1** and pass its
  `origin` as the SDK host. This does not change the destination port,
  URL scheme, SDK default, or public-host restrictions.
- Add source regression tests asserting numeric loopback and rejecting
  the previous `host: PROXY_BASE_URL` pattern.
- Separate GitHub Actions concurrency groups for ordinary push-driven
  browser E2E and explicitly opted-in real-ingestion E2E on the same
  commit. Otherwise the optional proof cancels the normal CI check and
  misleadingly appears as a failing Playwright run.

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
