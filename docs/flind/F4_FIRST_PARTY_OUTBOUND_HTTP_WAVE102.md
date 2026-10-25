# Wave 102 — Flind identity in first-party outbound OAuth / connection HTTP traffic

## Production behavior corrected

Three outbound HTTP `User-Agent` values from first-party Flind backend code advertised the inherited product identity. The following **actual runtime call sites** now use Flind names:

1. `posthog/api/posthog_connection.py` forwards an MCP-origin request as `flind-connection; <existing MCP marker>`, only if `mcp_origin=True`; the message shown when the connection's in-flight throttle rejects a request also says Flind.
2. `posthog/api/oauth/cimd.py` fetches an explicitly requested HTTPS OAuth Client ID Metadata Document (CIMD) using `Flind-CIMD/1.0`.
3. `posthog/api/oauth/client_assertion.py` fetches a client-provided JWKS document using `Flind-OAuth-JWKS/1.0`.

The HTTP header names, OAuth client IDs, authorization, exact-origin enforcement, SSRF pinning, credentials, reserved integration types, token cache keys and existing MCP-origin marker remain unchanged. No new destination, DNS, network request or vendor endpoint was introduced. Mandatory third-party licensing and attribution are unchanged.

## Tests

- **5/5** focused network-free tests in `tools/flind/test_outbound_identity_wave102.py` PASS. They execute the actual `_forward_through_connection` and `_fetch_jwks_document` source functions, not stand-in implementations, using a fake loopback-free request transport. Checked true/false MCP marking, sandbox origin header, bearer token isolation, no HTTP redirects, first-party JWKS/CIMD identity and the original API field names.
- **21/21** original Django `posthog.api.oauth.test_cimd.TestFetchCimdMetadata` tests PASS against patched source in an isolated Python 3.14.7 runtime with local, mocked HTTPS fetch. The original positive fetch test now asserts the actual `requests.Session.get` call advertises `Flind-CIMD/1.0`.
- `py_compile` and Git whitespace checks PASS.
- Test runtime used pinned free development-only Python packages `pytest==9.1.1`, `syrupy==6.1.1`, and `time-machine==3.5.1`, in addition to existing Wave100 developer packages. No project dependency lock files were changed. The older full test checkout's temporary changes were restored after the tests.

## Release limits

This is verified **first-party outbound client identity** and one real OAuth metadata test slice, not a qualified Flind OAuth issuer/PKCE/browser E2E or real cross-tenant authorization. The SDK→Capture Rust→Kafka→ClickHouse→API→dashboard product pipeline, zero-legacy source and distribution, TLS deployment profile and browser network egress remain blockers. Do not publish or change repo privacy / inherited GitHub Actions. Preserve legally required attribution.
