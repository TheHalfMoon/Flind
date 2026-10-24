# Flind F2 Wave 11 — standalone auth pages and local form assets

## Why

Two legacy standalone login/signup templates still used the prior product title,
could load the browser analytics SDK without an API token, and requested
Bootstrap CSS from an external CDN. The older HTML template also contained a
cloud-specific asset host rewrite. None belongs to Flind's independent
default-user experience.

## Changes

- Both `frontend/src/layout.html` and `frontend/src/layout.ejs` have a
  first-party Flind title.
- Browser analytics initialization is enclosed in the existing Django
  `not opt_out_capture and js_posthog_api_key` condition. A normal
  unconfigured Flind instance emits no SDK loader from these templates.
- When local self-capture is enabled, the SDK asset is resolved from the
  Flind frontend's exact current origin and fixed local `/static/array.js`
  path; no CDN alias or vendor-owned endpoint is used.
- Vendored Bootstrap 4.4.1 form CSS into
  `frontend/public/flind-form-foundation.min.css`, served as a
  same-origin static resource.
- Preserved the vendor's original MIT license at
  `frontend/public/flind-form-foundation.LICENSE`.
- Added template/static asset checks in
  `tools/flind/test_standalone_auth_forms.py`.

## Validation and limitations

- The new source checks verify both template guards, current-origin SDK
  URLs, first-party title, local stylesheet and preservation of legal notice.
- This work did not execute actual Django template rendering, Vite/Webpack
  output production, browser rendering or end-to-end login flows.
- The old browser SDK protocol namespace remains until the owned SDKs,
  ingestion pipeline and frontend imports are migrated together and proven.
- All old external URLs in other parts of the product are not removed yet.
- Continue to block release and retain source attribution and license notices.
