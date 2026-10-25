# Wave 106 — Production Capture v1 invalid-ack data-loss protection

## Real production defect fixed

Flind's first-party `posthog/api/capture.py` client previously treated an HTTP 200 `{"results": {"<event UUID>": {}}}` response as **successful delivery**. The response parser used `entry.get("result", "ok")`, so a receiver/proxy returning an object **without the mandatory `result` field** silently acknowledged an event that capture-rs never explicitly accepted. An unhashable `result` value (array/object) also crashed the parser's status-set check.

The parser now requires an **explicit string** member of the four known v1 statuses `ok`, `warning`, `drop`, `retry`. Any missing, unknown or malformed status becomes `{"result":"unaccounted"}`, *never* an acknowledgement; `raise_for_status()` fails. Known statuses and legitimate `retry` behavior are unchanged, so callers can retry only unaccounted events rather than resubmitting previously accepted events.

A second production defect was that a non-2xx response containing valid but non-object JSON (array/string/null) raised `AttributeError` when the error reporter called `.get()`. Such a reply now becomes an explicit `invalid_response` structured failure; non-JSON error responses retain their established bounded `unknown` error path.

No protocol header, endpoint, tenant ID, token, server config, Kafka consumer, database table, downstream schema, or required donor license was changed.

## Actual verification — October 26, 2026

- The original **complete Django `posthog.api.test.test_capture_internal` suite** executed against the **actual modified production module** in the isolated Python 3.14.7 full source environment: **180/180 PASS**, exit 0. Nine added cases exercise missing/null/list/object/number/unknown per-UUID status and non-dict HTTP error bodies (array/null/string). `raise_for_status()` is verified to fail rather than report success.
- **Real HTTP client loopback proof**, not a mocked Python requests transport: `tools/flind/qualify_invalid_capture_ack_wave106.py` launches a bounded private `127.0.0.1` `ThreadingHTTPServer`, runs **Flind's actual `capture_batch_internal`** in a sanitized independent Django subprocess and observes four real HTTP requests:
  1. HTTP 200 but missing per-event `result` => event is unaccounted, not success.
  2. HTTP 200 but per-event `result` is an array => unaccounted, no exception.
  3. HTTP 422 with JSON **array** error body => structured `invalid_response`, status 422, unaccounted, no uncaught error.
  4. Genuine HTTP 200 `{"result":"ok"}` => successful acknowledgment still works.
- Live HTTP proof exited **0**, all **6/6** qualification predicates PASS, exact four requests received only on loopback, first-party `flind-capture-v1-internal/1.0` SDK identity, synthetic token only. `HTTP_PROXY` and `HTTPS_PROXY` contain unusable loopback values to ensure internal service calls ignore ambient proxies.
- **21/21** focused Wave100/105/106 fixture unit tests PASS; Python byte compilation and Git diff whitespace gate PASS. The temporary full-checkout overlay was reverted after both actual test runs. No real customer data, external services, paid cloud or shared databases.

## Hard boundaries

The temporary receiver is **not** Rust capture-rs. The following proof flags remain deliberately **false**: `production_capture_rust_qualified`, `production_kafka_ingestion_qualified`, `product_clickhouse_schema_qualified`, `product_query_api_qualified`, `dashboard_e2e_qualified`, and `release_qualified`. A loopback-only request receipt is not a general network-egress audit.

Issue #82 remains open until the real SDK→Rust→Kafka→ClickHouse→authenticated query API→Dashboard, custom-user/tenant authorization, OAuth, frontend production build, Playwright and whole-source/binary branding gates pass. The repository remains private; inherited Actions disabled; no release/deployment.
