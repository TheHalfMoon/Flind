# Flind F2 Wave 10 — independent incident status feed

## Change

The inherited status source was a third-party incident/status page and was
polled every five minutes on regional cloud deployments. Flind should not
present another company's service availability as its own.

- The status feed has **no default destination**.
- `VITE_FLIND_STATUS_HOST` is an optional operator-configured bare DNS
  hostname for an independently controlled status provider.
- The first-party host validator rejects a full URL, port, credentials,
  malformed hostname, path and uppercase labels.
- The status loader returns null immediately without contacting any provider
  unless a valid host is configured **and** preflight identifies a regional
  deployment.
- Region-specific status links derive only from previously configured Flind
  US/EU hosts; there is no inherited cloud-host mapping.
- The Help menu, Today menu, status alerts and legacy side-panel no longer
  show unusable external status links when the host is unconfigured.
- The AI incident component name is Flind-specific rather than inherited.
- Updated source and regression tests for default no-egress.

## Verification

- 94 dependency-free Python unit/static checks PASS, 8 foundation assertions
  PASS.
- 8 modified TypeScript/TSX sources parse with TypeScript 5.9.3.
- Executed 9 status-host parser/default assertions in Node.
- git diff --check PASS.

## Required for real status service

Register/control a true Flind status domain and verify the API's
`/api/v1/summary` schema, incident groups, region routing, cache/CORS,
operational claims and browser polling behavior. Set the build-time variable
only after that qualification. No Flind status provider is represented as
operational by these changes.

Full Jest/Vitest, frontend typecheck, browser E2E and network-capture testing
NOT RUN. Source-wide legacy-identity removal remains FAIL. No release.
