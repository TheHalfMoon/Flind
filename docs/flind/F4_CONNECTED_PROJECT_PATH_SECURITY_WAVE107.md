# Wave 107 — Block encoded path traversal before forwarding connected-project OAuth tokens

## Production defect fixed

The connected-project Django API proxies an authorized user's requests with a stored OAuth bearer token using a fixed upstream origin, and previously validated only the **literal** submitted target API path. For example, it correctly rejected `api/../secret` but **accepted** `api/%2e%2e/admin/` and `api/%252e%252e/admin/`; intermediaries or upstream routes that percent-decode these may observe forbidden dot segments and path changes. The same validator also accepted encoded routing separators `%2f` and `%5c`, NUL/control characters and malformed escapes.

`posthog/api/posthog_connection.py` now validates a bounded `4096`-character relative path with valid percent-escapes, then iteratively inspects up to five decoding levels. It fails closed on:
- Encoded `..` traversal, standalone `.` segments, slash/backslash escapes, repeated `//`, scheme-like `://`, absolute/empty/protocol-relative paths
- Query/fragment separators inside a path, NUL and control characters, malformed percent escapes and invalid UTF-8
- Deeply nested encodings still changing beyond the inspection budget
- Unexpected non-string arguments.

Successful validation **returns the caller's original path** with its permitted encoding preserved. Thus an ordinary `api/projects/2/insights/` path, an optional single leading `/` (stripped like before), UTF-8 percent encoding, encoded spaces and literal `%25` are preserved. The endpoint path, OAuth token handling, permissions, upstream region selection, existing integration kind, `X-PostHog-Connection` marker, MCP marker, redirect refusal and required donor attribution remain unchanged.

## Observed evidence — October 26, 2026

Before the fix, executing the real source `_validate_target_path` accepted:
- `api/%2e%2e/admin/`
- `api/%252e%252e/secret/`
- `api/%2f%2fevil`
- `api/%00/secret`
- `api/%zz/`

The test `tools/flind/test_connection_path_security_wave107.py` executes the **actual production validator AST** and also the actual `_forward_through_connection` Python function with the real `requests` transport against an isolated, temporary `127.0.0.1` HTTP server. The local listener receives synthetic bearer tokens **only** for validated paths, observes **no** request for forbidden paths, receives safe encoded path strings unchanged, and returns an HTTP 307 redirect that the forwarding function **does not follow**.

**17/17** regression cases across Waves 102, 103, 107 PASS, with dozens of malicious/valid subcases. Python byte compilation and Git whitespace checks PASS. Original database-backed Django `TestPostHogConnectionForward` bad-path parametrization is extended for encoded evasions; running the full DB-backed original fixture remains a separate release qualification and is **not** claimed here.

## Limits

This closes a **validated path-check bypass**; it does not prove full product tenant authorization, configured OAuth issuer/client, real server/browser end-to-end, Rust capture production ingest or any public release readiness. The remote project still performs its own authorization. No paid cloud, external OAuth target, public service, shared user data or deployment was used. Keep repository private, inherited GitHub Actions disabled and legally required attribution intact.
