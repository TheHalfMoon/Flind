# Wave 66 — CSRF requires a verified personal API key

## Security defect

`posthog.middleware.CsrfOrKeyViewMiddleware` historically accepted an
unsafe request rejected by Django's CSRF middleware whenever
`PersonalAPIKeyAuthentication.find_key_with_source(request)` returned any
candidate. **Presence is not validity.** For example, supplying a
`?personal_api_key=fake` query parameter could bypass CSRF at middleware
time even when Django would later reject that as an invalid API credential.
Because some endpoints may authorize a session cookie separately, that
precondition violated the expected CSRF guard.

## Change

- First run the existing Django `CsrfViewMiddleware.process_view`.
- On a passed CSRF check, return immediately without examining keys.
- On a failed CSRF check, reject absent, nonstring, empty or >1024-character
  key candidates without hashing or database reads.
- Call the established `PersonalAPIKeyAuthentication.validate_key` on a
  well-formed candidate. It verifies a real active-user key and expiry,
  retaining the previous legitimate personal-key workflow, including
  header/body/query sources.
- Only accept the CSRF exception if that validation succeeds. A revoked,
  expired or invented key returns the original CSRF rejection.
- Preserve database and other unexpected errors as errors; do **not** turn
  failed verification into permission to pass CSRF. No raw keys are logged.
- Downstream API authentication and authorization remain unchanged. The
  middleware does **not** grant any privileges merely by validating a key.

The custom middleware remains in its existing position. Adding another
`django.middleware.csrf.CsrfViewMiddleware` to silence `security.W003`
would change processing order and potentially break valid personal-key
clients; that unrelated change is **not** part of this security fix.

## Executed local evidence — October 25, 2026

- **8/8 PASS** exact-source middleware regression tests with an isolated
  validator stub: normal CSRF, missing key, forged key via header/body/query,
  expired key, valid key, ill-typed/oversized input, unexpected database
  errors and anti-regression source contract.
- **PASS** real Django CSRF middleware behavioral probe using Django 5.2.18
  from the frozen Python 3.14.7 environment:
  `no_token_rejected=true`, `fake_key_rejected=true`,
  `valid_key_accepted=true`.
- No real provider tokens, sessions, database or network services were used.
  The Django probe compiles the actual Flind middleware class and supplies
  a synthetic credential validator. It is **not** a production HTTP login
  test, nor a test of the full application boot.
- The production change should be additionally verified against an
  isolated full backend's cookie-authenticated POST, valid legacy and
  current personal API keys, OAuth and CORS paths before publishing.

## Reproduction

```sh
python3 -m unittest tools.flind.test_csrf_personal_key_wave66 -q
# With the frozen Django/DRF runtime:
python -m tools.flind.qualify_csrf_personal_key_wave66
```

## Deployment status

`security.W003` may still be emitted by Django's generic deployment
check because it does not recognize the custom *subclass* of the built-in
CSRF middleware. This warning must be investigated with real requests
rather than suppressed globally or misrepresented as resolved.

Keep the repo private, GitHub Actions disabled, no paid services,
publication or deployment. Preserve legally required source notices.
Release qualification remains false until full backend and E2E tests.
