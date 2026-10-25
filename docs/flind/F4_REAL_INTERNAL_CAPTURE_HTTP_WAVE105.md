# Wave 105 — Real Flind internal Capture v1 HTTP client against an isolated loopback receiver

## What became real

Unlike Wave100's mocked Django capture HTTP calls and Wave101's Kafka CLI synthetic relay, this runs **Flind's actual `posthog.api.capture.capture_batch_internal`** with its real `requests.Session`, real JSON serialization, real HTTP request headers and retries, against a process-owned, bound-to-`127.0.0.1` temporary HTTP fixture.

No actual Rust capture-rs, Kafka broker or ClickHouse data is involved in **this** qualification. The receiver is a strict synthetic protocol fixture and all input data is constructed by the test. Do not confuse a successful receiver response with production ingestion.

## Real run — October 26, 2026

Using frozen Python 3.14.7 dependencies and a full Django source checkout, over a dedicated loopback-only `ThreadingHTTPServer`, **exit 0** and `real_internal_capture_http_client_qualified=true`. The actual source's SDK header is `flind-capture-v1-internal/1.0`; required `PostHog-*` HTTP **header names** remain for Rust-v1 protocol compatibility.

The test asserts:
- Request 1 contains **two** exact synthetic events and correctly-shaped capture-v1 envelope, sent with first-party SDK identity and synthetic Bearer token.
- Response 1 accepts event A and asks to retry event B; **request 2 contains B only**, with attempt count incremented from 1 to 2. Event A is never submitted again.
- A separate third request gets deliberately malformed `200` JSON, which Flind's actual producer classifies as unaccounted/failed (not success).
- A replay `$snapshot` event is **rejected by the producer before any additional HTTP call**; exactly three requests hit the fixture.
- The requested capture URLs resolve to the local loopback fixture even when fake `HTTP_PROXY`/`HTTPS_PROXY` variables are set; the internal HTTP helper uses `trust_env=False`. The receiver stores no bearer tokens. **This is not a global DNS/network-egress audit of the application.**

No real customer event, account credential, shared database, paid endpoint, cloud Kafka or deploy. The fake receiver and subprocess terminate after testing; no long-lived service remains.

## Test coverage and strict gates

**12/12** focused Wave105 and Wave100 tests passed using the real loopback protocol stub, Python syntax checks and Git whitespace checks. The fixture also guards bad paths and oversized/invalid request envelopes; all project release receipt fields remain false:

- `capture_rust_server_qualified`
- `production_kafka_event_ingestion_qualified`
- `clickhouse_product_events_qualified`
- `tenant_authorization_qualified`
- `dashboard_browser_e2e_qualified`
- `release_qualified`

Remaining Issue #82 release gates include actual Rust receiver, Kafka consumer, production event schema/read API, browser dashboard, full OAuth/tenant testing, production frontend/desktop build and whole-source/binary branding. Keep repo private, inherited Actions disabled, attribution intact, no release/deployment.
