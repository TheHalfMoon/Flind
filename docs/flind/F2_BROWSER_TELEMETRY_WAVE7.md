# F2 Wave 7 — Flind browser telemetry defaults off

## Observed risk

The server-rendered browser bootstrap embedded an analytics API key and an
external collection host from the source project's cloud when both self-capture
and E2E mode were off. Merely renaming the UI did not remove this egress path.

## Implementation

- Removed the inherited browser collection host and token constants entirely
  from the first-party backend code path.
- Created a small pure `flind/browser_capture.py` selection function so default
  production, local self-capture, and E2E fixture behavior can be tested without
  a running database.
- Normal pages with `SELF_CAPTURE=false` never receive a browser capture
  token or host, even when the context caller prepopulates legacy fields.
- `SELF_CAPTURE=true` retains browser self-capture only when the selected
  local team supplies an API token; the browser uses the current Flind origin.
- E2E mode also defaults to no collection; an operator may set
  `FLIND_E2E_CAPTURE_TOKEN` for same-origin fixture capture only.
- Existing `OPT_OUT_CAPTURE` template guard remains active.
- Three new Django context tests verify the actual backend entrypoint in
  addition to the pure helper tests.

## Tests and limitations

- 77 dependency-free Python tests PASS, including 10 new capture tests.
- 8 existing basic brand assertions PASS.
- Python compilation on touched server modules and new tests PASS.
- Django integration tests ADDED but **NOT RUN**, because the current isolated
  Python environment lacks Django and product dependencies.
- No browser/network E2E, real ingestion telemetry trace, or full app
  bootstrap check was run.

## Open release gates

- Legacy protocol field and SDK names still exist in other components;
  comprehensive refactor must be staged with integration and database tests.
- Older standalone template entrypoints and CSP/static asset loads need a
  separate egress audit.
- Source-wide identity gate and full release qualification are still FAIL.
- Keep inherited licenses and true third-party attribution as required.
- No publication.
