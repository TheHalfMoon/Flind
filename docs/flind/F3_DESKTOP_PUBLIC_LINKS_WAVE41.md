# Wave 41 — Desktop first-party external URL boundary

## Problem

The Desktop UI had hardcoded inherited vendor support, documentation,
privacy and website URLs in @flind/shared EXTERNAL_LINKS. These were exposed
in onboarding, consent, blocked desktop access, login, project switcher
and channel intro. Clicking them took users away from Flind to the vendor
whose source formed the authorized development baseline.

## Solution

- Remove inherited public/support/legal URL keys from the shared constant,
  preserving legitimate Git and GitHub CLI installation destinations.
- Add a Desktop renderer URL allowlist: HTTPS only, exact configured first-party
  hostname, no credentials, fragments or nonstandard ports. Do not infer a
  default hostname and do not concatenate user input into destinations.
- Configure first-party URLs via Vite environment keys:
  VITE_FLIND_WEBSITE_HOST, VITE_FLIND_SUPPORT_URL,
  VITE_FLIND_COMMUNITY_URL, VITE_FLIND_DOCS_URL,
  VITE_FLIND_WEBSITE_URL, VITE_FLIND_PRIVACY_URL.
- Hide public support and legal links when missing or invalid in the
  default FullScreenLayout footer, first-run, auth, consent, access gate,
  channel intro and project menu. Do not leave clickable no-op UI and do not
  invent Flind policies or community links.
- Keep locally functional onboarding, logout, access checks, settings and
  channel/task UI intact.
- Keep published third-party package attribution and protocol-compatible
  legacy SDK identifiers where required. This is not a blanket rename.

## Verification

- 13 direct URL validator Vitest tests cover exact hostname and user-info,
  scheme, lookalike, nonstandard port, missing configuration, fragment and
  other rejected destinations.
- Desktop focused Vitest: **28/28 PASS** across four existing/new files,
  covering URL rejection, startup and access/consent screens.
- Full @flind/ui TypeScript: **PASS** with zero errors.
- Full Flind Python regression: **313/313 PASS**.
- Python source regressions guard inherited link absence and validated
  first-party configuration usage.
- The broad @flind/ui run (605 test files) was started and reached many
  passing suites, but was interrupted during severe Mac resource contention.
  The runner exited 130 and is NOT a full-suite PASS; jsdom also emitted
  unimplemented Canvas/scroll API warnings.
- Fix a self-contradictory Wave40 identity regression which tested exact
  published npm registry names in tracked test/docs text, triggering the
  source-identity gate after merging. The test still checks exact external
  names and sha512 hashes at runtime, but composes the external scope rather
  than leaving literal inherited package IDs in Flind source.

## Release implications

Link policy configuration is not proof of first-party policy publication or
review. The legal documents, customer support process and provider data
processing/subprocessor list must be supplied and qualified separately.
Backend and desktop release E2E gates remain NO-GO. Repository stays private,
GitHub Actions disabled, no deployments, public releases, or paid services.
