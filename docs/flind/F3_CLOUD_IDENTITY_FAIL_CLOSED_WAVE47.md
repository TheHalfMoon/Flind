# Wave 47 — Hosted Cloud, OAuth identity and credential egress fail closed

## Blocking finding

The central agent-contracts getCloudUrlFromRegion still contained
hardcoded externally hosted donor cloud origins for three production/dev-cloud
regions. getOauthClientIdFromRegion also returned inherited OAuth
application IDs. These helpers are used by the Desktop agent, browser app,
API clients, model gateways and integrations. Earlier local UI link fixes
did not protect these API and token flows.

## Central qualification change

- Preserve region IDs us, eu, dev-cloud for API compatibility; remove
  their hardcoded remote destinations.
- Require an operator-configured Cloud URL and separately registered,
  nonempty OAuth public client ID for each hosted region:
  FLIND_US_CLOUD_URL, FLIND_US_OAUTH_CLIENT_ID,
  FLIND_EU_CLOUD_URL, FLIND_EU_OAUTH_CLIENT_ID,
  FLIND_DEV_CLOUD_URL, FLIND_DEV_CLOUD_OAUTH_CLIENT_ID.
- Node runtimes read the plain environment names. Vite browser builds read
  VITE_-prefixed equivalents; these are URLs and public OAuth client IDs,
  NOT client secrets or bearer tokens.
- Validate every hosted pair using the existing strict custom-cloud schema:
  HTTPS for non-loopback hosts, root origin only, no query or fragment,
  nonempty OAuth ID and no built-in inherited vendor host.
- Harden that shared validator further: reject URLs with embedded usernames
  or passwords.
- Throw an explicit "Flind Cloud is not configured" error without a valid
  pair. Do not fall back to the original vendor, an empty string or the
  current browser origin, even when an old region value is persisted.
- Keep the local development loopback http://localhost:8010 distinct.
  Existing custom cloud configuration still works when explicitly configured;
  no hosted region silently inherits it.
- Update region labels so the UI does not display the old vendor hosts.

## Evidence and limits

- Full @flind/agent-contracts suite: **858/858 PASS** across 31 test files, including the browser Vite public-configuration path.
- Real build (tsup ESM and DTS) and TypeScript: PASS.
- Runtime smoke of the built dist: unconfigured us, eu, dev-cloud
  block, while an explicitly configured Flind US URL and OAuth ID resolve.
- Harness OAuth regression: **31/31 PASS**.
- Browser Web OAuth tests: **3/3 PASS** with stubbed fetch. Confirm no
  token fetch without configuration, verified Flind endpoint/client ID
  when configured, and refusal of an inherited provider domain.
- Web OAuth and actual Cloud runtime smoke ran with test URLs and stubbed
  fetch; no external authentication provider was contacted.
- Full Flind Python regressions: **333/333 PASS**.
- Flind source guards for cloud identity: **5/5 PASS**.
- @flind/core TypeScript: **PASS**, zero errors.
- @flind/web TypeScript: **PASS**, zero errors, after frozen no-script
  installation of Web and Host Router dependencies.
- @flind/ui TypeScript: **PASS**, zero errors on second run. First run
  exited 134 from Node V8 heap OOM with a 2.3 GiB cap; rerunning at
  3.4 GiB on the 8 GiB Mac completed successfully.
- Source formatting and staged whitespace checks: PASS.

## Remaining release blockers

This does NOT provision Flind infrastructure, register OAuth clients,
configure proper scopes, qualify a real token exchange, or provide
Django/Postgres/ClickHouse/Redis ingestion and query E2E. It deliberately
leaves hosted sign-in unavailable until those are independently qualified.
The local Mac has PostgreSQL 17.9, but the active Python environment lacks
Django/Redis/ClickHouse dependencies and Docker's daemon is stopped. The
8 GB Mac is unsuitable for claiming full stacked service coverage without
resources or separate qualified runners.

No deployment, public release, network token submission or paid services.
The GitHub repository remains private, inherited Actions disabled and
third-party legal notices preserved.
