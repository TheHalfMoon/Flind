# F2 Wave 6 — independent Flind OAuth sessions and API hosts

## Security boundary

The imported frontend used another product's registered OAuth clients, cloud
origins, ingestion, live events, and public-webhook hosts. Stored bearer tokens
could also be forwarded when a destination shared a string prefix with the
configured backend origin.

## Implementation

- OAuth region hosts now come from `VITE_FLIND_REGION_US_HOST` and
  `VITE_FLIND_REGION_EU_HOST` (already used by Flind region navigation).
- OAuth public client IDs require `VITE_FLIND_OAUTH_US_CLIENT_ID` and
  `VITE_FLIND_OAUTH_EU_CLIENT_ID`, both blank by default.
- No OAuth flow starts unless both the first-party HTTPS origin and a properly
  shaped client ID are configured. The local developer OAuth controls are
  hidden when no registered Flind regions exist.
- Authorization and token exchange reject a pending state whose host/client
  pair does not match the operator-configured Flind region.
- Browser sessions now use `flind_oauth_session` and are ignored unless all
  session fields and exact host/client identity pass validation. Old stored
  credentials are not accepted; logout clears the legacy key.
- The debug-only SPA OAuth-mode cookie is now `flind_oauth_mode` on both
  backend and frontend; logout clears the previous cookie.
- Bearer credentials are sent only when the parsed request URL origin exactly
  equals the configured backend origin (never a string-prefix comparison).
- App API and webhooks origins no longer route to inherited cloud endpoints;
  the livestream keeps its server-supplied endpoint or local fallback.
- Corrected a stale error-linkification test fixture from the earlier
  same-origin-content hardening.

## Evidence

- Source-driven dependency-free unit/static tests in `tools/flind`.
- Independent Node execution of transpiled OAuth source checks default denial,
  exact Flind host/client binding, session repudiation and logout behavior.
- TypeScript 5.9.3 syntax transpilation for changed files.
- Python syntax verification and `git diff --check`.

## Deployment prerequisites / remaining blockers

A first-party OAuth issuer must register and publish the **actual** Flind
public client IDs, redirect URIs, CORS allowlists and token endpoints. A
first-party host variable alone is not proof of registration.

Full frontend Jest/Vitest, Django integration, PKCE with a real server,
CORS checks, OAuth refresh/revocation, browser E2E and runtime egress
qualification remain required. No cloud identity or OAuth client is claimed
to be operating now. The source-wide zero-identity gate still fails;
the debug cookie handshake stays DEBUG-only and is not a production
authentication mechanism. No release.
