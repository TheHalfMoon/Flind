# Wave 103 — Flind public errors and OpenAPI for project connections

## Source change

The connected-project Django REST endpoint used several inherited product names in its API errors and generated OpenAPI schema. This was externally observable even after Wave102 rebranded the outbound `User-Agent`.

`posthog/api/posthog_connection.py` now uses **Flind connection** in missing/expired grant messages, unclear token-scope refusal, nested connection refusal, nonexistent connection, creator-only authorization, and public API schema summaries/descriptions. Its region description now identifies a **configured** region instead of asserting cloud hosting. No HTTP path, Django model field, endpoint, stored integration kind, authentication, request body shape or response status changed.

**Preserved compatibility:** the existing `X-PostHog-Connection` forward marker, `POSTHOG_CONNECT_KIND` database identifier, cross-region routing function, MCP marker and all OAuth protocol requirements are unchanged. Legal third-party attribution is untouched.

## Verification

- **6/6** new network-free Wave103 regression tests PASS. They compile and invoke the **actual** token-selection, scope-enforcement, forward-loop refusal and missing-connection methods, verifying Flind-first-party error payload text while preserving the authentication and wire namespace. OpenAPI schema decorator metadata is checked from the real AST.
- **5/5** Wave102 actual function outbound HTTP tests still PASS (**11/11 combined**).
- Python source compilation and Git whitespace checks PASS.

## Bounds

These are meaningful production API messages and generated OpenAPI labels, not a complete source identity migration. Database-backed Django connection authorization and real E2E remain untested in this wave; issue #82 remains open. Keep the Flind repo private and Actions disabled. No deployment, publication or paid providers.
