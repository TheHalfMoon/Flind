# Wave 28 — Mobile native app and deep-link identity (not deployment)

## Observed source risk

The imported Expo app declared an original-provider app name, slug, URL
scheme, iOS/Android bundle ID, verified universal-link entitlements, EAS
project ID and publishing owner. OAuth callbacks, GitHub callbacks and MCP
installation returned through that inherited URL scheme. Links were built
with a claimed host that Flind does not control.

## Implemented

- Identify the unshipped app as Flind with the flind:// custom scheme,
  provisional com.thehalfmoon.flind.mobile iOS/Android IDs, and Flind
  permissions copy. These package IDs are provisional; store ownership and
  entitlement must be confirmed independently.
- Remove the inherited EAS project ID and owner. Do not create or deploy a
  replacement without the founder's explicit release decision.
- Remove iOS universal associated domains and Android auto-verified URL
  intent filters. An unrelated vendor's hostname must not be claimed.
- Require explicit EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN before generating
  universal HTTPS URLs. Validate HTTPS origin, reject inherited provider
  hosts, embedded URL credentials and extra paths/query/fragments.
- Reject incoming URLs that do not use the Flind app scheme or the exact
  configured HTTPS origin.
- Update Expo OAuth, MCP and GitHub callback URI strings consistently with
  the new flind:// native scheme. Preserve backend parameter names used
  for protocol compatibility.
- Do not invent or serve Apple AASA, Android assetlinks, Flind domain,
  OAuth client registration or app-store record.
- The backend may still require inherited callback whitelists: this is an
  explicit release blocker requiring integrated testing and corresponding
  backend/native contract migration.

## Evidence

- Real transpiled TypeScript deep-link module behavioral tests: 18/18 PASS,
  including missing origin, accepted new scheme, rejected inherited scheme
  and hosts, rejecting HTTP and hidden URL components.
- Changed TS/TSX parser 9 files / zero diagnostics; Flind Python suite
  261/261 PASS, and git diff --check PASS (macbook 2026-10-24).
- Full Expo native build, TestFlight, associated domains, Android app links,
  OAuth backend and OS callbacks are NOT qualified in this checkout.

NO-GO for release. Repository private; inherited Actions disabled; no
deployment, EAS registration or publishing. Required legal attribution intact.
