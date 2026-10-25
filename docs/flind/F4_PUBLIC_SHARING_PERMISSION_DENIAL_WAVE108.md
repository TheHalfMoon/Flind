# Flind Wave 108 — Explicit permission denials must stop public query sharing

## Production change

`posthog/api/query_access_check.py::denied_query_resources` is the shared access-control compiler used by public-link publication, editing already exposed insights, subscribing dashboards and updating shared notebooks. Before this wave, it caught `UserAccessControlError` and `TableAccessDeniedError` but **silently swallowed every other exception**, including a Django/DRF `PermissionDenied` raised by a query runner, compilation or policy hook. The caller then saw an empty denial list and could allow the public share to proceed.

The checker now explicitly re-raises `django.core.exceptions.PermissionDenied` and `rest_framework.exceptions.PermissionDenied`. A public share's `denied_resources_in_share`/sharing endpoint propagates this denial and stops the enable transition. The existing named table/resource-denial report is preserved.

**Intentional compatibility:** general non-authorization query parser/compile errors are still skipped. The original Django sharing test `test_unparseable_query_does_not_block_publishing` explicitly expects an invalid, unexecutable query not to block publishing, because it fails on the read side regardless. Unknown query kinds that cannot be resolved are unchanged. No user, team, query, SQL, OAuth token, API endpoint, migrations, Redis or ClickHouse configuration was altered.

## Evidence — October 26, 2026

- **11/11** focused tests PASS in `tools/flind/test_public_share_permission_gate_wave108.py`; they extract and execute the real `denied_query_resources` function AST with controlled query runners and test explicit Django and DRF permission errors at runner-level authorization and SQL compilation, plus a real `denied_resources_in_share` function extract to verify share-gate propagation.
- Named table/resource access denial reports remain unchanged; valid queries still resolve; unparseable queries and unknown runner kinds keep their existing behavior.
- Both actual framework exception classes and their import paths were verified available from the isolated Python 3.14.7 runtime (`django.core.exceptions.PermissionDenied` and `rest_framework.exceptions.PermissionDenied`).
- Python compilation and Git whitespace checks PASS. No DB backed original full Django sharing suite executed for this wave; this is a focused code-path correction, not full production tenant/public-link E2E.

## Limitations

This change prevents an explicit permission denial from being downgraded to a normal query error in the shared access-control compiler. It does **not** establish that all queries and all exceptions are safely classified, or qualify enterprise authorization, public sharing, all cross-team filters, full OAuth/PKCE, Rust Capture→Kafka→ClickHouse→Dashboard, frontend build, browser E2E or Flind's release. Issue #82 and the other applicable release gates remain open.

Keep private repository, disabled inherited Actions, no deployment/publication/paid cloud and mandatory third-party legal attribution.
