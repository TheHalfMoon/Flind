# Wave 44 — First-party only Desktop org/project creation navigation

## Confirmed inherited data-flow exposure

The Desktop ProjectSwitcher still built create-organization,
create-project and organization-logo media URLs from a region-based
inherited provider cloud endpoint. Even after public marketing/legal
links were guarded in Wave 41, menu actions could open the vendor's
host and fetch organization media directly from that origin.

## Implemented boundary

- Add a strict first-party Cloud App URL resolver using explicitly
  configured VITE_FLIND_CLOUD_APP_HOST and VITE_FLIND_CLOUD_APP_URL.
- Require exact HTTPS hostname, uncredentialed default port, a clean
  root URL and a single-leading-slash relative route. Reject inherited
  vendor hosts, username injection, near-match hosts and protocol-relative
  or backslash paths.
- Hide project/organization creation actions unless a verified Flind
  cloud-app URL exists; no fake URL, disabled but apparently active
  button, or hardcoded provider fallback.
- Resolve organization logo requests only against verified Flind cloud
  app host and percent-encode the media identifier.
- Preserve local organization/project switching, logout, settings, archived
  tasks and independently verified public/website links.

## Evidence

- 27 direct Vitest URL cases exercise the marketing/legal boundary and the
  independent cloud navigation resolver, including all adversarial paths.
- Python source guard checks the configured host boundary and absence of
  region-based vendor URL use in this menu.
- Full @flind/ui TypeScript: **PASS**, zero errors.
- Full Flind Python source suite: **323/323 PASS**.
- Focused first-party cloud navigation tests: **27/27 Vitest PASS**.
- Python source guard: **3/3 PASS**.
- Staged whitespace check: PASS.

## Critical remaining release limitations

The broader Flind Desktop OAuth, cloud API clients, SDK URLs, billing
flows, web auth and media routes still need first-party host and
identity qualification. This patch is not a claim that all egress is
contained. The independently operated Flind backend is not yet proven,
and there is no deployed or verified cloud-app configuration.

No publication or deployment; repo remains private, inherited GitHub
Actions disabled, and third-party attribution preserved.
