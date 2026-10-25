# Wave 104 — Real Django HTTP login + CSRF with Flind SessionStore, disposable PostgreSQL

## Verified scope

`tools/flind/qualify_http_login_wave104.py` exercises the **real Django HTTP test Client**, auth backend, session middleware, CSRF middleware and **actual Flind `posthog.session.backend.SessionStore`** using **a fresh, private, loopback PostgreSQL 17 cluster** and synthetic accounts. It extends Wave64's direct session-storage test with actual HTTP POST/GET lifecycle behavior.

The application ships a *custom* `posthog.User` model and thousands of app migrations. This test deliberately creates only the framework's disposable `auth.User` table inside the isolated database after applying core `auth` and `posthog_session` migrations. The scoped migrations correctly omit `auth_user` because Flind normally swaps the Django user model. **This is not a production Flind user/login/auth or tenant test**; test code never modifies product migrations, application models, existing databases or user accounts.

Django's actual CSRF enforcement on HTTPS-like test requests checks a same-origin `Referer`, not just the CSRF cookie/header. Negative and positive probes supply valid same-origin `Referer` values where appropriate so a missing/malicious CSRF token fails **for the intended reason**, rather than a missing HTTPS referrer.

## Actual live evidence — Mac, October 26, 2026

`/tmp/flind-wave63-runtime/bin/python -m tools.flind.qualify_http_login_wave104 --json` in a checked-out source tree with locked dependencies and private PostgreSQL toolchain:

**Exit 0; `framework_http_login_flind_sessionstore_qualified=true`**.

All **10/10** live predicates passed:
1. Reject a same-origin HTTPS login POST without a CSRF token.
2. Reject login when a hostile `Origin` contradicts the trusted same-origin `Referer`.
3. Reject incorrect password.
4. Accept correct password through real Django `authenticate` + `login` and read `request.user` through the HTTP middleware stack.
5. Persist the authenticated user's ID in the actual Flind custom `django_session` table.
6. Keep a separate HTTP client unauthenticated before login.
7. Preserve unique, independent sessions for two distinct synthetic users.
8. Reject an unsafe logout POST without CSRF while preserving the logged-in user.
9. Revoke the server session on valid logout; a separate client replaying the old session ID stays anonymous.
10. Refuse authentication when the second user's server-side session expiration is in the past.

The test uses random synthetic passwords, ephemeral PostgreSQL SCRAM credentials, no real user data, no third-party endpoints, and no shared login sessions. The temporary cluster is stopped and deleted. Mac retained ~15 GiB free disk.

**8/8** additional isolated guard tests passed for migration ordering, dependency-lock admission, fake positive receipts, missing PostgreSQL, missing child results and explicit production auth/tenant/browser gate separation. Python compile and Git whitespace checks passed.

## Release claims intentionally false

`flind_custom_user_login_qualified=false`, `production_middleware_stack_qualified=false`, `product_oauth_qualified=false`, `tenant_authorization_qualified=false`, `browser_playwright_qualified=false`, `release_qualified=false`.

This is **framework HTTP + first-party Flind session-store proof**, not complete product login/tenant/browser E2E. Real frontend build, Flind production models and SDK→Capture Rust→Kafka→ClickHouse→Dashboard remain to be proven under Issue #82. Private repo, inherited Actions disabled, no deployment, no paid cloud, attribution untouched.
