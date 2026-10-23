# F2 Wave 2 — first-party region redirect boundary

## Problem

The imported login flow accepted hard-coded SaaS region destinations and an
unused browser redirect module could construct an external URL from a cookie.
Neither belongs in an independent Flind distribution.

## Flind implementation

- `flind/region_redirect.py` is the new Flind-owned, dependency-free hostname validator.
- Redirect hostnames can only come from operator-set `FLIND_REGION_HOST_US` and
  `FLIND_REGION_HOST_EU`. Values are bare lowercase DNS names.
- `FLIND_APP_HOST` must be set to the exact app hostname before any redirect
  runs. All three host settings default to the empty string.
- `FLIND_REDIRECT_TO_PRIMARY` is a separate opt-in boolean (default false).
- A cookie alone cannot authorize a redirect: non-HTTPS, credentials, ports,
  paths, fragments, queries, invalid hostnames and non-allowlisted origins fail closed.
- Removed the unused client-side cross-region redirect component and its obsolete
  fixture, which previously contained inherited provider hostnames.
- Added replacement Django test cases for configured first-party redirects,
  unknown domains, empty defaults and primary fallback.

### Example *fictional* operator configuration

```dotenv
FLIND_APP_HOST=app.flind.example
FLIND_REGION_HOST_US=us.flind.example
FLIND_REGION_HOST_EU=eu.flind.example
FLIND_REDIRECT_TO_PRIMARY=false
```

These `example` values are not registered endpoints or deployment instructions;
use verified Flind-owned domains only when multi-region hosting exists.

## Evidence

- `PYTHONPATH=. python3 -m unittest discover -s tools/flind -p 'test_*.py' -q`:
  27 standard-library tests PASS in the scoped checkout.
- `python3 tools/flind/check_brand_entrypoints.py`: 8 checks PASS.
- `python3 -m py_compile`: changed Python settings, backend and test sources PASS.
- `git diff --check`: PASS.

Full Django integration tests are written but **not yet executed**; this
environment has no installed Django application dependencies. Live DNS/HTTP
instrumentation is also pending. Therefore F2 remains BLOCKED.

## Compatibility and cleanup still needed

The cookie name and internal Django Python module/setting names retained in
unmodified import surfaces remain migration work, not a claim of final
Flind identity. Product SDKs must not silently rename protocol identifiers
without migrating every producer/consumer. Source-wide zero-identity gate stays
failing until all active paths, text and final binary distributions are clean.
