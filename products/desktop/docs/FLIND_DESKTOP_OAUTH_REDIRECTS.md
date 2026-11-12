# Flind desktop OAuth: credential redirects fail closed

Flind desktop's core OAuth implementation has two secret-bearing token POSTs:
`refreshToken` sends a refresh token; `exchangeCodeForToken` sends a one-time
authorization code and PKCE verifier. Previously both used Fetch's default
redirect policy, which may forward the credential body to another origin after
a 307/308 response from the selected host.

Both request sites now set `redirect: "error"`; surfaced HTTP 3xx responses
are rejected before accepting or parsing tokens. Authorization-code exchange
does not retry a surfaced redirect. Refresh reports an unknown OAuth response
error rather than marking the user's token revoked or signed out.

Synthetic Vitest checks cover 301, 302, 303, 307, 308 for both paths and
assert one POST only to the originally selected URL. This does not contact
Flind Cloud or another service. The desktop and browser OAuth clients are
separate, and both require independent verification.

**NO-GO:** The operator must provision and own the OAuth client IDs, HTTPS
server and callback registration, and test actual Windows/macOS Electron
runtime networking for redirect egress, PKCE/state/CSRF checks, and token
refresh/revocation. This is an additional boundary, not proof of a finished
OAuth service or authorization to publish a binary.
