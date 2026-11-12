# OAuth token transport redirect policy

Flind mobile's authorization-code exchange, refresh-token exchange and best-effort revocation all send secret-bearing bodies to the **selected authenticated host**. They must never follow a 301, 302, 303, 307 or 308 response to a different endpoint. The transport explicitly requests `redirect: 'error'`; token requests also reject any 3xx response surfaced by the adapter.

The app still permits intentionally selected HTTPS self-hosted servers, and it is not a guarantee that every React Native platform honors Fetch redirect policies. **Before mobile distribution:** use instrumented native iOS and Android builds against a synthetic redirecting test server, verify no outgoing request reaches a second host, and capture network traces for approval. If the native adapter ignores the option, replace it with an audited no-redirect transport, not an allowlist exception.

This patch changes no backend OAuth scopes, cookies, keys, account registration, or session expiry. All test credentials and destinations are synthetic. No external service was contacted.
