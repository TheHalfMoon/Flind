# Flind — independent security contact publication (F2 Wave 8)

## Problem

The inherited `/.well-known/security.txt` endpoint published an unrelated
company's security email/careers address and an already expired record.

## Implemented

- No security contact is advertised by default; the endpoint returns HTTP 404.
- Operator configuration is exclusively `FLIND_SECURITY_CONTACT` and
  `FLIND_SECURITY_EXPIRES`, both empty by default.
- `flind/security_contact.py` emits a minimal valid `Contact:` and
  `Expires:` record only for safe HTTPS or mailto contacts and a timezone-aware
  future expiry no more than 365 days away.
- Rejects CRLF/header injection, invalid authorities, fragments, expired
  and implausibly long validity windows.
- Added pure-Python checks and Django HTTP regression tests.

## Release considerations

- A verified security inbox or HTTPS disclosure URL **must** be provided by
  the Flind operator before publishing this endpoint.
- There is no invented inbox or unrelated employer name in default responses.
- Empty default (404) is intentional and should become a configured valid
  record before a public launch.

## Verification

- 7 new dependency-free tests PASS.
- Python syntax compilation PASS.
- The Django HTTP tests were authored but NOT RUN: Django is not installed
  in this isolated test environment.
- Full app tests and zero-identity gate remain blocked. No release.
