# Wave 135 — Remove inherited Desktop signup cutoff default

## Product defect

`posthog/settings/web.py` inherited a donor Desktop rollout date of `2026-10-01T00:00:00+00:00` for every non-test deployment. The first-party `products/tasks/backend/access.py` implementation computes whether `user.date_joined` is at or after that configured cutoff when the legacy Desktop signup gate is enabled. A fresh Flind installation should not inherit the unrelated donor's enrollment date, particularly before Flind has qualified its own Desktop account policy.

## Change

`DESKTOP_SIGNUP_CUTOFF` now defaults to the empty string for both test and normal operation. `_signup_cutoff()` already treats empty as `None`, so the cutoff-dependent block is inactive by default. Operators who intentionally configure an ISO-8601 timestamp retain the exact existing date comparison and explicit invalid-timestamp error. No user account records, feature flag keys, endpoint routing, billing, database schema or Desktop implementation paths were modified.

**Important compatibility constraint:** The actual `posthog-desktop-signup-gate` and access-override feature flag keys remain inherited and must be migrated in a coordinated rollout; changing identifiers without updates to stored flags or runtime tests could silently change policy. This wave does not claim that all other Desktop access checks are disabled.

## Executed evidence

Fetched the exact GitHub branch into the connected Mac without changing its existing Flind checkout. Ran `FLIND_SOURCE_ROOT=<Flind> python3 tools/flind/test_wave135_desktop_cutoff.py --ref FETCH_HEAD -v`. The test evaluates the **actual assigned settings AST expression**, compiles the original `_signup_cutoff` and `_signed_up_after_cutoff` function bodies from Git-tracked `products/tasks/backend/access.py`, and passes synthetic in-memory join dates. **4/4 PASS, exit 0** (~10 seconds).

- No configured cutoff: `_signup_cutoff()` returns `None`, new users do not trigger date-based refusal.
- Explicit `2026-10-01` cutoff: users before are not flagged; users at or after are flagged.
- Malformed configured timestamps raise `DesktopAccessResolutionError`.
- An explicit empty override remains disabled.

## Remaining gates

No real Django HTTP/Desktop session, user/billing authorization, cross-project flag migration, service runtime or browser E2E was run in this wave. Flind release blockers #5 and #82 remain open, as do independent auth/OAuth and network qualifications. Keep private repo, inherited Actions disabled, no publishing/deploying or paid services, and legally required notices intact.
