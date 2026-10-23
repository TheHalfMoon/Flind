# F2 Wave 3 — Flind-owned frontend region destinations

## Risk addressed

Legacy browser views and internal admin helpers could navigate to inherited US/EU
cloud hosts even though Flind does not operate them. The old `CLOUD_HOSTNAMES`
table was not an acceptable default.

## Implementation

- Added `frontend/src/lib/flindRegionHosts.ts`.
- The only approved destinations are bare hostnames explicitly configured at build:
  `VITE_FLIND_REGION_US_HOST` and `VITE_FLIND_REGION_EU_HOST`.
- The validator refuses paths, URLs, credentials, ports, malformed labels,
  protocol-relative paths and unconfigured regions.
- Removed `CLOUD_HOSTNAMES` from the frontend constants and migrated every
  direct consumer: region picker, secondary region login hint, signup maintenance
  redirect and staff impersonation login links.
- When neither Flind region is configured, the cloud selector stays hidden and
  no cross-region URL is generated. This intentionally disables the inherited
  cloud UX rather than redirecting Flind users elsewhere.
- Renamed the local impersonation return action to `returnToFlind`.
- Updated existing frontend tests and added a new Flind region-host test suite.

## Tested

- 46 dependency-free Python static/unit tests PASS.
- 8 original identity checks PASS.
- 11 changed TS/TSX files parse successfully with TypeScript 5.9.3.
- A Node execution of transpiled Flind helper functions passed 10+ origin/path
  assertions, including blank config, configured domains, invalid hosts and paths.
- `git diff --check` PASS.

## Still blocking release

- Full TypeScript type checking, Vitest suites and browser flow E2E NOT RUN.
- Region/registration UX needs genuine Flind-owned deployed endpoints and API
  verification before enabling cloud multi-region behavior.
- Old SDK protocol names and unrelated references remain throughout the source.
- The strict zero-identity gate still FAILS, as do independence/release gates.

No Flind regional domain is implied by the `.example` test fixtures. No release.
