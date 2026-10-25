# Wave 68 — Browser session cookies cannot inherit a personal-key CSRF exemption

## Exploit boundary

The preceding Wave 66 change required a real validated personal API key
before waiving CSRF. This was necessary but not sufficient. A valid key
owned by account A can be placed into a cross-origin form or URL sent to
a browser authenticated with account B's **session cookie**. At this
middleware position, `AuthenticationMiddleware` has not yet attached
`request.user`. Simply verifying A's valid key could therefore waive
B's CSRF check even if a later view uses B's session authentication.

This change removes that ambiguity rather than guessing the intended
authentication identity. For an unsafe request rejected by Django CSRF:

- If a cookie matching `settings.SESSION_COOKIE_NAME` is present at all,
  **return the original CSRF rejection**. This is true for an empty,
  malformed or stale cookie, and for any API key from any source.
- Only cookie-free clients may use the Wave 66 validated-personal-key
  exception. Their key still must pass the existing active-user,
  expiry and cryptographic verification.
- Cookie-bearing clients remain free to submit a valid CSRF token,
  regardless of whether an API key is also present.
- Other unrelated cookies do not block standalone API-key clients.
- Respect a configured/custom session cookie name instead of hardcoding
  `sessionid`.
- Don't query or validate API keys when the session-cookie boundary has
  already rejected the request.

The intentional compatibility change is that API clients which
previously sent **both** a session cookie and a personal key but no CSRF
token now get CSRF 403. Such clients must omit the session cookie or
supply the normal CSRF token. No automatic token-to-session fallback.

## Executed evidence — October 25, 2026

- Wave 68 + existing Wave 66 exact-source regression tests:
  **15/15 PASS**.
- Real Django 5.2.18 CSRF middleware behavior with Flind's compiled
  actual middleware class, isolated key-validator stub:
  `no_token_rejected=true`, `fake_key_rejected=true`,
  `valid_key_accepted=true`,
  `valid_key_with_session_cookie_rejected=true`. **PASS**.
- Full real HTTP session, OAuth, downstream identity routing, browser
  CSRF cookies and multi-tenant E2E are **not** qualified by this
  isolated test. Issue #82 remains open.

Run without network, from repo root:

```sh
python3 -m unittest \
  tools.flind.test_csrf_cookie_boundary_wave68 \
  tools.flind.test_csrf_personal_key_wave66 -q

# Exact frozen Django/DRF runtime required:
python -m tools.flind.qualify_csrf_personal_key_wave66
```

No new dependency or provider service, no shared database data or source
attribution change. Keep the repository private, inherited Actions
disabled, no paid service or public release/deployment.
