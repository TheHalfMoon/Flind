# Flind real-ingestion cross-tenant personal API key denial

Status: **PR #83 merged after its exact-head full real-service E2E passed**
([run 43408588563](https://github.com/TheHalfMoon/Flind/actions/runs/43408588563),
commit `75623997d02fff48fe12a7090dca65a931bab5f7`, three ingestion
suites and four general browser journeys). This follow-up PR #86 disables
redirect following for the foreign personal-key probe. Re-qualify CI
and real-service E2E on its **own** head before considering integration.

## Why existing ingestion isolation was necessary but not sufficient

A successfully persisted synthetic event followed by an unrelated team's
count of zero proves the query engine filters events by tenant. It does not
prove that Flind's API authorization rejects a personal key belonging to
one organization when asked to query another organization's team ID.

The CI test setup creates **distinct users** with distinct personal keys,
organizations and teams. The positive proof for one owner and successful
zero-count query from the second owner establish both keys work when used
with their own teams; then the test probes **both directions**:

1. Team B's valid personal API key attempts Team A's query endpoint.
2. Team A's valid personal API key attempts Team B's query endpoint.

Both must return **401, 403 or 404**, never HTTP 2xx (even if the count
looks zero). A 5xx error fails as a bug rather than being counted as
authorization protection. Request bodies and credentials are never
printed in the helper's diagnostics, and the expected event is synthetic.

## Scope

A common Playwright helper provides this negative request. It is
invoked in the real direct capture E2E, the real Node SDK E2E and the
locally hosted browser SDK E2E *after* positive event persistence and
independent-team zero count assertions.

The browser SDK test now uses the same strict `parseHogQLCount` shape
validation as other ingestion tests so malformed/missing rows cannot
be mistaken for a zero, whether on the origin or negative control.

The isolated CI contract checks source wiring without starting real
services. The existing `flind-e2e.yml` continues to require the
explicit **`ingestion=true`** manual opt-in for a test that brings up
PostgreSQL, ClickHouse, Kafka, Redis, Django, Rust capture/ingestion and
Chromium. No new ports or external telemetry endpoints are added.

## Boundaries and future acceptance

This is one **real-time analytics query authorization** path. It does
not claim all API routes, ingestion keys, exports, file uploads, data
warehouse endpoints, organizations' roles, or superuser permissions
are fully isolated. For those, negative server-side campaigns and
adversarial browser/device workflows remain necessary.

Production release remains **NO-GO** until independently owned
packages, endpoints, operational backups/upgrade paths, security
audits and cross-platform QA are qualified. Never publish public
artifacts without founder's explicit `GREEN LIGHT FLIND`.
