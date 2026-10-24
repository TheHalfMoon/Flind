# Wave 46 — Guard all Desktop UI project links against inherited cloud hosts

## Finding

The UI's shared compatibility-named getPostHogUrl function still returned
ANY http/https absolute URL unchanged, including values from server-side
task/run records, or joined a relative path to inherited cloud-region
hosts. This bypassed the opt-in first-party link and billing boundaries
added in Waves 41–45.

## Behavior change

- Keep the helper name/signature for downstream source compatibility.
- Require an independently configured Flind cloud app root URL before
  returning either a relative or absolute navigation URL.
- Reject absolute links unless their HTTPS scheme, exact hostname, port,
  credentials, fragment and origin pass the same first-party checks.
- For relative links, use only the independently configured Flind app host,
  never region-derived original provider URLs.
- Reject protocol-relative, malformed, lookalike, other schemes and
  backslash-confusion URLs. Existing product link-building utilities
  continue to generate paths and encoded query fragments.
- Preserve legacy region argument types without treating region labels
  as authorization to send users to an external original vendor.

## Evidence

- The real getPostHogUrl and Cloud App URL resolver receive Vitest cases
  for internal routes, region independence, absolute trusted links and
  adversarial input. They do not mock the helper itself.
- Python source regression prevents a raw absolute URL passthrough or
  cloud-region dependency being reintroduced.
- First-party navigation and URL-security Vitest: **51/51 PASS**.
- Downstream link-building and share link Vitest: **49/49 PASS**.
- Full @flind/ui TypeScript: **PASS**, zero errors.
- Full Flind Python source regression suite: **328/328 PASS**.
- Two source protection regressions and staged whitespace: PASS.

## Remaining NO-GO

This does not alter or qualify the independent OAuth flows, API clients,
provider model endpoints, backend web routes, SDK ingestion, billing service
or mobile network connections. A verified URL is not proof that a first-party
Flind Cloud application is deployed or fully functional. All these items
remain release blockers. Repository private, inherited Actions disabled,
no deployment or paid services.
