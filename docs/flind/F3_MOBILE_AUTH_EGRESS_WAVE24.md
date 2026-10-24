# F3 Wave 24 — Mobile OAuth and API destination isolation

## Observed risk

The copied mobile application still had hardcoded original-vendor cloud API
origins for US/EU and original vendor OAuth client registration IDs. These
values were used to construct authorization, token exchange, refresh, and
authenticated API destinations even when the user had not provisioned any
Flind-controlled hosted endpoints.

## Change

- Remove inherited hosted API origins and OAuth client IDs from first-party
  mobile auth constants.
- Require explicit Expo build-time `EXPO_PUBLIC_FLIND_API_US_URL` and
  `EXPO_PUBLIC_FLIND_API_EU_URL` to enable respective hosted regions.
- Require explicit `EXPO_PUBLIC_FLIND_OAUTH_*_CLIENT_ID` per environment.
- Preserve opt-in loopback development (`http://localhost:8010`) but refuse
  remote plaintext HTTP. The default is not a hosted service.
- Validate HTTPS origin, reject inherited cloud apex/subdomains (including
  trailing DNS root dots), and reject credentials, paths, queries, fragments,
  and surrounding whitespace.
- OAuth token exchange and refresh fetch use `redirect: "error"` to avoid
  following an unexpected HTTP 3xx while transmitting an authorization code
  or refresh token.
- Change mobile User-Agent values to `flind/mobile`. Leave existing internal
  provenance/compatibility wire fields untouched pending contract testing.
- Document the new keys in the mobile `.env.example`; no credentials or actual
  hosted environment were configured.

## Qualification, 2026-10-24, macbook

- Dependency-free behavioral checks executed the transpiled real constants
  implementation: **16/16 passed** (missing config, explicitly configured
  TLS/loopback, forbidden vendor host/redirectable credential URLs, OAuth ID).
- Python mobile boundary regression: **6/6 passed**.
- Full Flind Python regression: **245/245 passed**, rerun after User-Agent updates.
- TypeScript parser: no syntax diagnostics in changed TS/TSX source.
- **Mobile Vitest / Expo native tests were not run** because dependencies
  are not installed in this Mac checkout. New Vitest test cases are
  committed for later qualified execution.

## Open release blockers

Device/browser OAuth app-link registration, Expo build config and app identity,
real HTTP network tracing, token refresh on-device, OS-native build, complete
UI/SDK rebranding and end-to-end login all remain unqualified. Do not publish
or deploy Flind; repository remains private and GitHub Actions disabled.
