# Wave 43 — No inherited vendor sales/games links in Desktop access gate

## Risk

The Flind Desktop blocked-access page previously described eligibility
using the original provider's startup/YC program and prepaid credits,
told users to contact that vendor's sales account executive, and offered
a game at their external website if registrations were paused. These
claims and navigation destinations do not belong to Flind.

## Change

- Replace the inherited reason-specific marketing/legal copy with
  neutral Flind messaging tied only to the server's actual block status.
- Preserve the server-reported reason tags (startup_plan, prepaid_credits,
  null-for-signups-paused) for compatibility; do not infer a new policy.
- Remove the unrelated external game/button and vendor sales email.
- Keep functional retry, project/organization switching, login and logout.
- Preserve existing analytics that reports the access block status.
- Do not introduce unverified first-party external links.

## Validation

- The original DesktopAccessScreen Vitest file runs with nine cases;
  it now asserts that the externally hosted vendor game/sales destinations
  are unavailable and confirms local recovery actions.
- Additional Flind Python source regressions prevent the inherited links
  and verify the screen retains the server-policy actions.
- Full @flind/ui TypeScript: **PASS**, zero errors.
- Full Flind Python source regression suite: **320/320 PASS**.
- Original DesktopAccessScreen Vitest: **9/9 PASS**.
- Three additional Python source/route assertions: PASS.

## Limitations

The underlying access policy is still supplied by the compatibility
backend; Flind operator entitlement/eligibility semantics need independent
product decisions and service-level tests. No claim is made of completed
auth or organization policy integration. Private repository, inherited
GitHub Actions disabled; no paid service, deployment or public release.
